import datetime
import math
import sys

import json

import circuit
import fetcher
import logging
from sqlalchemy import select
from database import SessionLocal
from models import Race, DriverResult, LapPosition, PitStop, SprintResult, RaceMeta, CircuitMap, IngestState, get_or_create_meta


def _to_int(value):
    """int(value), or None for None/NaN/non-numeric (FastF1 uses NaN for missing)."""
    try:
        if value is None or math.isnan(float(value)):
            return None
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


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
        logging.warning("Circuit lookup failed for %s key %s: %s", year, circuit_key, e)
        return None
    if built is None:
        return {**base, "status": "unavailable", "reason": reason, "data": None}
    return {**base, "status": "available", "reason": None, "data": data}


def backfill_circuit_maps(retry_unavailable=False, today=None) -> list:
    """Add circuit maps to stored races that have none. Returns names still without one.

    Lookups that raised are not recorded and are retried next run; "unavailable"
    answers are only retried when `retry_unavailable` is set.
    """
    db = SessionLocal()
    try:
        races = [(r.race_id, r.name, r.round, r.date) for r in db.query(Race).order_by(Race.date)]
    finally:
        db.close()

    missing = []
    for race_id, name, rnd, date in races:
        if not date or rnd is None:
            continue
        db = SessionLocal()
        try:
            row = db.get(CircuitMap, race_id)
            if row is not None and not (retry_unavailable and row.status == "unavailable"):
                continue
            year = int(date[:4])
            values = None
            try:
                key = fetcher.get_circuit_key(fetcher.load_session_info(year, rnd))
                values = prepare_circuit_map(year, key, today=today)
            except Exception as e:
                logging.warning("Circuit backfill failed for %s: %s", name, e)
            if values is None:
                missing.append(name)
                continue
            if row is None:
                row = CircuitMap(race_id=race_id)
                db.add(row)
            for k, v in values.items():
                setattr(row, k, v)
            db.commit()
            if values["status"] != "available":
                missing.append(name)
        except Exception as e:
            db.rollback()
            logging.warning("Circuit backfill failed for %s: %s", name, e)
            missing.append(name)
        finally:
            db.close()
    return missing


def _load_sprint(year, race):
    """Sprint results as a list, or None if the sprint can't be loaded right now."""
    try:
        sprint_session = fetcher.load_sprint_session(year, race)
        if sprint_session is None:
            return None
        return fetcher.get_sprint_results(sprint_session)
    except Exception as e:
        logging.warning("Sprint load failed for %s %s: %s", year, race, e)
        return None


def _add_sprint_rows(db, race_id, sprint_results):
    for driver in sprint_results or []:
        position = _to_int(driver["Position"])
        if position is None or position < 1:
            continue
        db.add(SprintResult(
            race_id=race_id,
            position=position,
            full_name=driver["FullName"],
            team=driver["TeamName"],
            points=fetcher.finite_number(driver.get("Points")),
            status=driver.get("Status"),
        ))


def sprint_retry_delay_days(attempts: int) -> int:
    """Days to wait before the next sprint load: 0, 2, 4, then weekly (never gives up)."""
    return 0 if attempts <= 0 else (2 ** attempts if attempts < 3 else 7)


def _record_sprint_attempt(db, race_id, today):
    meta = get_or_create_meta(db, race_id)
    meta.sprint_attempts = (meta.sprint_attempts or 0) + 1
    meta.sprint_last_attempt = today.isoformat()


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


def _replace_sprint(db, race_id, results, state, today):
    state.sprint_required = True
    old_count = db.query(SprintResult).filter_by(race_id=race_id).count()
    valid = [r for r in results or [] if (_to_int(r.get("Position")) or 0) > 0]
    if not valid or len(valid) < old_count:
        _record_sprint_attempt(db, race_id, today)
        return False
    db.query(SprintResult).filter_by(race_id=race_id).delete()
    _add_sprint_rows(db, race_id, valid)
    state.sprint_refreshed_at = today.isoformat()
    state.sprint_complete = len(valid) == len(results)
    if not state.sprint_complete:
        _record_sprint_attempt(db, race_id, today)
    else:
        meta = db.get(RaceMeta, race_id)
        if meta:
            meta.sprint_attempts = 0
            meta.sprint_last_attempt = None
    return state.sprint_complete


def backfill_sprints(year, events, today=None) -> list:
    """Retry missing/partial sprints and periodically refresh stored classifications.

    Returns the names of races whose sprint is still unavailable. Each failed
    attempt is recorded in `race_meta`, and a race is only retried once its backoff
    (see `sprint_retry_delay_days`) has passed, so a permanently unavailable sprint
    costs at most one session load a week instead of one per daily run.
    """
    today = today or datetime.date.today()
    pending = []
    for event in events:
        if not event["has_sprint"]:
            continue
        db = SessionLocal()
        try:
            race = (
                db.query(Race)
                .filter(Race.date.like(f"{year}-%"), Race.round == event["round"])
                .first()
            )
            if race is None:
                continue
            state = db.get(IngestState, race.race_id)
            if state and not refresh_due(race.date, state.sprint_refreshed_at, state.sprint_complete, today):
                if not state.sprint_complete:
                    pending.append(event["name"])
                continue
            meta = db.get(RaceMeta, race.race_id)
            if not _sprint_retry_due(meta, today):
                pending.append(event["name"])
                continue
            sprint_results = _load_sprint(year, event["round"])
            if state is None:
                state = IngestState(race_id=race.race_id)
                db.add(state)
            if not _replace_sprint(db, race.race_id, sprint_results, state, today):
                pending.append(event["name"])
            db.commit()
        except Exception as e:
            db.rollback()
            logging.exception("Sprint backfill failed for %s", event["name"])
            pending.append(event["name"])
        finally:
            db.close()
    return pending


def run_pipeline(year, race, has_sprint=False, force_sprint=False) -> bool:
    """Ingest one race (and its sprint) in a single transaction. Returns True on success.

    `race` may be a round number (preferred: FastF1 matches names fuzzily) or a name.
    Re-running updates the race identified by (season, round) and keeps its race_id.
    The sprint is optional: if it cannot be loaded the race is still stored, and
    `run_pending_races` retries the sprint on later runs (see `backfill_sprints`).
    Existing sprint rows are never dropped just because the sprint failed to load.
    """
    db = None
    try:
        session = fetcher.load_session(year, race)
        if session is None:
            raise RuntimeError(f"could not load race session for {year} {race}")
        result = fetcher.get_race_results(session)
        if not result or not any(_to_int(r.get("Position")) == 1 for r in result):
            raise ValueError("Race has no usable classification or winner; retry later")
        lap_data = fetcher.get_lap_data(session)
        pitstop = fetcher.get_pitstop_data(session)
        race_info = fetcher.get_race_info(session)
        fastest_lap = fetcher.get_fastest_lap(session) or {}
        try:
            weather = fetcher.get_weather_data(session)
        except Exception:
            logging.exception("Weather unavailable for %s %s", year, race)
            weather = {"air_temp": None, "track_temp": None, "rainfall": None}

        # None = unavailable/not requested: leave any stored sprint rows untouched.
        sprint_attempted = has_sprint
        if has_sprint and not force_sprint:
            # Race refreshes must not bypass the sprint retry schedule or count
            # a skipped lookup as a failed attempt.
            with SessionLocal() as lookup:
                stored = lookup.query(Race).filter(
                    Race.date.like(f"{year}-%"), Race.round == race_info["round"]
                ).first()
                meta = lookup.get(RaceMeta, stored.race_id) if stored else None
                sprint_attempted = _sprint_retry_due(meta, datetime.date.today())
        sprint_results = _load_sprint(year, race) if sprint_attempted else None
        if not sprint_results:
            sprint_results = None
        if sprint_attempted and sprint_results is None:
            print(f"Sprint data unavailable for {year} {race}; storing the race without it")

        # Optional enrichment: a failure here must never block the race itself.
        circuit_values = prepare_circuit_map(year, fetcher.get_circuit_key(session))

        db = SessionLocal()

        existing = (
            db.query(Race)
            .filter(Race.date.like(f"{year}-%"), Race.round == race_info["round"])
            .first()
        )
        if existing:
            # Lock the parent before replacing children; uniqueness protects first inserts.
            db.execute(select(Race).where(Race.race_id == existing.race_id).with_for_update())
        race_row = existing or Race()
        old_lap_count = db.query(LapPosition).filter_by(race_id=race_row.race_id).count() if existing else 0
        if old_lap_count > sum(1 for lap in lap_data if (_to_int(lap.get("Position")) or 0) > 0):
            raise ValueError("Refusing to replace fuller lap data with partial data")
        old_result_count = db.query(DriverResult).filter_by(race_id=race_row.race_id).count() if existing else 0
        usable_results = [r for r in result if (_to_int(r.get("Position")) or 0) > 0]
        if old_result_count > len(usable_results):
            raise ValueError("Refusing to replace a fuller classification with partial results")
        for key, value in {
            "name": race_info["name"], "location": race_info["location"],
            "date": race_info["date"], "round": race_info["round"],
            "total_laps": race_info["total_laps"],
            "fastest_lap_driver": fastest_lap.get("driver"),
            "fastest_lap_time": fastest_lap.get("lap_time"),
            "fastest_lap_number": fastest_lap.get("lap_number"),
            "fastest_lap_team": fastest_lap.get("team"),
            "air_temp": fetcher.finite_number(weather["air_temp"]),
            "track_temp": fetcher.finite_number(weather["track_temp"]),
            "rainfall": None if weather["rainfall"] is None else ("Yes" if weather["rainfall"] else "No"),
        }.items():
            if existing and value is None and key in {"air_temp", "track_temp", "rainfall",
                    "fastest_lap_driver", "fastest_lap_time", "fastest_lap_number", "fastest_lap_team"}:
                continue
            setattr(race_row, key, value)
        db.add(race_row)
        db.flush()
        for model in (PitStop, DriverResult, LapPosition):
            db.query(model).filter(model.race_id == race_row.race_id).delete()

        for pit in pitstop:
            db.add(PitStop(
                race_id=race_row.race_id,
                driver=pit["Driver"],
                lap_number=int(pit["LapNumber"]),
                old_compound=pit["OldCompound"],
                new_compound=pit["NewCompound"],
            ))

        for driver in result:
            position = _to_int(driver["Position"])
            if position is None or position < 1:
                print(f"Skipping {driver.get('FullName')}: no finishing position")
                continue
            db.add(DriverResult(
                race_id=race_row.race_id,
                position=position,
                grid_position=_to_int(driver.get("GridPosition")),
                full_name=driver["FullName"],
                abbreviation=str(driver.get("Abbreviation", "")),
                team=driver["TeamName"],
                time=str(driver["Time"]),
                fastest_lap=str(driver.get("FastestLapTime", "")),
                points=fetcher.finite_number(driver.get("Points")),
                status=driver.get("Status"),
            ))

        for lap in lap_data:
            position = _to_int(lap["Position"])
            if position is None or position < 1:
                continue
            db.add(LapPosition(
                race_id=race_row.race_id,
                driver=str(lap["Driver"]),
                lap_number=int(lap["LapNumber"]),
                position=position,
            ))

        if circuit_values:
            row = db.get(CircuitMap, race_row.race_id)
            if row is None:
                row = CircuitMap(race_id=race_row.race_id)
                db.add(row)
            # An empty response must not replace an already usable map.
            if row.status != "available" or circuit_values["status"] == "available":
                for key, value in circuit_values.items():
                    setattr(row, key, value)

        state = db.get(IngestState, race_row.race_id)
        if state is None:
            state = IngestState(race_id=race_row.race_id)
            db.add(state)
        state.race_refreshed_at = datetime.date.today().isoformat()
        state.race_complete = (len(usable_results) == len(result)
            and len(usable_results) >= len({lap["Driver"] for lap in lap_data})
            and any((_to_int(lap.get("Position")) or 0) > 0 for lap in lap_data))
        if has_sprint:
            state.sprint_required = True
            if sprint_attempted:
                _replace_sprint(db, race_row.race_id, sprint_results, state, datetime.date.today())

        db.commit()
        return True

    except Exception as e:
        logging.exception("Pipeline failed for %s %s", year, race)
        if db:
            db.rollback()
        return False

    finally:
        if db:
            db.close()


def run_pending_races(year, today=None) -> list:
    """Fetch missing races and refresh classifications when their retry interval is due.

    Returns the names of races that failed so the caller can exit non-zero.
    Missing/partial sprint data is retried with backoff and reported as a warning.
    """
    today = today or datetime.date.today()
    db = SessionLocal()
    try:
        existing = {}
        for r in db.query(Race).filter(Race.date.like(f"{year}-%")).all():
            state = db.get(IngestState, r.race_id)
            existing[r.round] = (r.date, state.race_refreshed_at if state else None,
                                 state.race_complete if state else False)
    finally:
        db.close()

    failed = []
    events = fetcher.get_completed_races(year)
    for event in events:
        stored = existing.get(event["round"])
        if stored and not refresh_due(*stored, today=today):
            continue
        print(f"Fetching {event['name']} (round {event['round']})...")
        if not run_pipeline(year, event["round"], has_sprint=event["has_sprint"]):
            failed.append(event["name"])

    try:
        backfill_circuit_maps(today=today)
    except Exception as e:  # enrichment only: never fail the ingest run
        logging.exception("Circuit map backfill skipped")

    sprint_pending = backfill_sprints(year, events, today=today)
    if sprint_pending:
        print(f"Sprint results still unavailable for: {', '.join(sprint_pending)}")

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
