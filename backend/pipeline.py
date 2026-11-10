import datetime
import sys

import json

import circuit
import fetcher
import logging
from database import SessionLocal
from models import Race, RaceMeta, CircuitMap, IngestState
from ingest_data import normalize_race, normalize_sprint
from race_store import store_race, store_circuit, replace_sprint

logger = logging.getLogger(__name__)


def prepare_circuit_map(year, circuit_key, today=None):
    """Row values for `circuit_maps`, or None if the source could not be reached.

    None means "ask again next run". A source that answers without usable data is
    stored as status "unavailable" so it is not asked again every day.
    """
    today = (today or datetime.date.today()).isoformat()
    base = {"circuit_key": circuit_key, "source": "multiviewer", "fetched_at": today}
    if circuit_key is None:
        return {**base, "status": "unavailable", "reason": "no_circuit_key", "data": None}
    try:
        raw = fetcher.fetch_circuit_payload(year, circuit_key)
        built, reason = circuit.build_circuit_map(raw)
        data = json.dumps(built, separators=(",", ":"), allow_nan=False) if built else None
    except Exception as e:
        logger.warning("Circuit lookup failed for %s key %s: %s", year, circuit_key, e)
        return None
    if built is None:
        return {**base, "status": "unavailable", "reason": reason, "data": None}
    return {**base, "status": "available", "reason": None, "data": data}


def backfill_circuit_maps(retry_unavailable=False, today=None) -> list:
    """Backfill optional geometry without holding a connection during downloads."""
    with SessionLocal() as db:
        races = db.query(Race.race_id, Race.name, Race.round, Race.date).order_by(Race.date).all()
    missing = []
    for race_id, name, rnd, date in races:
        if not date or rnd is None:
            continue
        try:
            with SessionLocal() as db:
                row = db.get(CircuitMap, race_id)
                if row is not None and not (retry_unavailable and row.status == "unavailable"):
                    continue
            year = int(date[:4])
            key = fetcher.get_circuit_key(fetcher.load_session_info(year, rnd))
            values = prepare_circuit_map(year, key, today=today)
            if values is None:
                missing.append(name)
                continue
            with SessionLocal.begin() as db:
                store_circuit(db, race_id, values)
            if values["status"] != "available":
                missing.append(name)
        except Exception:
            logger.exception("Circuit backfill failed for %s", name)
            missing.append(name)
    return missing


def _load_sprint(year, race):
    """A normalized sprint payload, or None when it cannot be loaded."""
    try:
        sprint_session = fetcher.load_sprint_session(year, race)
        if sprint_session is None:
            return None
        return normalize_sprint(fetcher.get_sprint_results(sprint_session))
    except Exception as e:
        logger.warning("Sprint load failed for %s %s: %s", year, race, e)
        return None


def sprint_retry_delay_days(attempts: int) -> int:
    """Days to wait before the next sprint load: 0, 2, 4, then weekly (never gives up)."""
    return 0 if attempts <= 0 else (2 ** attempts if attempts < 3 else 7)


def _sprint_retry_due(meta, today) -> bool:
    if meta is None or not meta.sprint_last_attempt:
        return True
    last = datetime.date.fromisoformat(meta.sprint_last_attempt)
    return (today - last).days >= sprint_retry_delay_days(meta.sprint_attempts or 0)


def refresh_due(race_date, refreshed_at, complete, today):
    """Daily for incomplete/recent races, weekly otherwise. Legacy rows refresh once."""
    if not refreshed_at:
        return True
    age = (today - datetime.date.fromisoformat(race_date)).days
    interval = 1 if not complete or age <= 14 else 7
    return (today - datetime.date.fromisoformat(refreshed_at)).days >= interval


def backfill_sprints(year, events, today=None) -> list:
    """Download due sprints outside transactions; retry failures with backoff."""
    today = today or datetime.date.today()
    pending = []
    for event in events:
        if not event["has_sprint"]:
            continue
        try:
            with SessionLocal() as db:
                race = db.query(Race).filter(
                    Race.date.like(f"{year}-%"), Race.round == event["round"]
                ).first()
                if race is None:
                    continue
                race_id = race.race_id
                state = db.get(IngestState, race_id)
                if state and not refresh_due(race.date, state.sprint_refreshed_at, state.sprint_complete, today):
                    if not state.sprint_complete:
                        pending.append(event["name"])
                    continue
                if not _sprint_retry_due(db.get(RaceMeta, race_id), today):
                    pending.append(event["name"])
                    continue
            sprint = _load_sprint(year, event["round"])
            with SessionLocal.begin() as db:
                # Serialize writers before checking the retry marker again.
                db.query(Race).filter_by(race_id=race_id).with_for_update().one()
                if not _sprint_retry_due(db.get(RaceMeta, race_id), today):
                    continue
                state = db.get(IngestState, race_id)
                if state is None:
                    state = IngestState(race_id=race_id)
                    db.add(state)
                if not replace_sprint(db, race_id, sprint, state, today):
                    pending.append(event["name"])
        except Exception:
            logger.exception("Sprint backfill failed for %s", event["name"])
            pending.append(event["name"])
    return pending


def run_pipeline(year, race, has_sprint=False, force_sprint=False, today=None) -> bool:
    """Download and normalize first, then save one race in an atomic transaction."""
    today = today or datetime.date.today()
    try:
        session = fetcher.load_session(year, race)
        if session is None:
            raise RuntimeError(f"could not load race session for {year} {race}")
        info = fetcher.get_race_info(session)
        try:
            weather = fetcher.get_weather_data(session)
        except Exception:
            logger.exception("Weather unavailable for %s %s", year, race)
            weather = {"air_temp": None, "track_temp": None, "rainfall": None}
        payload = normalize_race(
            info=info, rows=fetcher.get_race_results(session), lap_data=fetcher.get_lap_data(session),
            pits=fetcher.get_pitstop_data(session), fastest=fetcher.get_fastest_lap(session) or {}, weather=weather,
        )
        sprint_attempted = has_sprint
        if has_sprint and not force_sprint:
            with SessionLocal() as lookup:
                stored = lookup.query(Race).filter(
                    Race.date.like(f"{year}-%"), Race.round == info["round"]
                ).first()
                meta = lookup.get(RaceMeta, stored.race_id) if stored else None
                sprint_attempted = _sprint_retry_due(meta, today)
        sprint = _load_sprint(year, race) if sprint_attempted else None
        if sprint_attempted and (sprint is None or not sprint.results):
            logger.warning("Sprint data unavailable for %s %s; preserving any stored sprint", year, race)
        circuit_values = prepare_circuit_map(year, fetcher.get_circuit_key(session), today=today)
        with SessionLocal.begin() as db:
            store_race(db, year=year, payload=payload, circuit=circuit_values, sprint=sprint,
                       has_sprint=has_sprint, sprint_attempted=sprint_attempted, today=today)
        return True
    except Exception:
        # This is the job boundary: report a failed race to the caller/CLI.
        # Session.begin rolls back every write if validation or persistence fails.
        logger.exception("Pipeline failed for %s %s", year, race)
        return False


def run_pending_races(year, today=None) -> list:
    """Fetch missing races and refresh classifications when their retry interval is due.

    Returns the names of races that failed so the caller can exit non-zero.
    Missing/partial sprint data is retried with backoff and reported as a warning.
    """
    today = today or datetime.date.today()
    db = SessionLocal()
    try:
        existing = {}
        rows = db.query(Race, IngestState).outerjoin(IngestState, Race.race_id == IngestState.race_id)
        for r, state in rows.filter(Race.date.like(f"{year}-%")).all():
            existing[r.round] = (r.date, state.race_refreshed_at if state else None,
                                 state.race_complete if state else False)
    finally:
        db.close()

    failed = []
    events = fetcher.get_completed_races(year, today=today)
    for event in events:
        stored = existing.get(event["round"])
        if stored and not refresh_due(*stored, today=today):
            continue
        logger.info("Fetching %s (round %s)", event["name"], event["round"])
        if not run_pipeline(year, event["round"], has_sprint=event["has_sprint"], today=today):
            failed.append(event["name"])

    try:
        backfill_circuit_maps(today=today)
    except Exception:  # enrichment only: never fail the ingest run
        logger.exception("Circuit map backfill skipped")

    sprint_pending = backfill_sprints(year, events, today=today)
    if sprint_pending:
        logger.warning("Sprint results still unavailable for: %s", ", ".join(sprint_pending))

    return failed


if __name__ == "__main__":
    from database import engine
    from migrate import check_schema
    import argparse
    parser = argparse.ArgumentParser(description="Ingest and refresh completed races without generating summaries")
    parser.add_argument("--year", type=int, default=datetime.date.today().year)
    parser.add_argument("--round", type=int, help="Force refresh a specific round")
    parser.add_argument("--has-sprint", action="store_true", help="Include sprint results with --round")
    args = parser.parse_args()
    check_schema(engine)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.round is not None:
        sys.exit(0 if run_pipeline(args.year, args.round, has_sprint=args.has_sprint, force_sprint=args.has_sprint) else 1)
    failed_races = run_pending_races(args.year)
    if failed_races:
        print(f"Failed races: {', '.join(failed_races)}")
        sys.exit(1)
