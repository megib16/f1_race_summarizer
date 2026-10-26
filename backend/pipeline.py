import datetime
import math
import sys

import json

import circuit
import fetcher
import summarizer
from database import SessionLocal
from models import Race, DriverResult, LapPosition, PitStop, SprintResult, RaceMeta, CircuitMap, get_or_create_meta


def _to_int(value):
    """int(value), or None for None/NaN/non-numeric (FastF1 uses NaN for missing)."""
    try:
        if value is None or math.isnan(float(value)):
            return None
        return int(value)
    except (TypeError, ValueError):
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
    except Exception as e:
        print(f"Circuit lookup failed for {year} key {circuit_key}: {e}")
        return None
    built, reason = circuit.build_circuit_map(raw)
    if built is None:
        return {**base, "status": "unavailable", "reason": reason, "data": None}
    return {**base, "status": "available", "reason": None, "data": json.dumps(built, separators=(",", ":"))}


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
                print(f"Circuit backfill failed for {name}: {e}")
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
            print(f"Circuit backfill failed for {name}: {e}")
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
        print(f"Sprint load failed for {year} {race}: {e}")
        return None


def _add_sprint_rows(db, race_id, sprint_results):
    for driver in sprint_results or []:
        position = _to_int(driver["Position"])
        if position is None:
            continue
        db.add(SprintResult(
            race_id=race_id,
            position=position,
            full_name=driver["FullName"],
            team=driver["TeamName"],
        ))


def sprint_retry_delay_days(attempts: int) -> int:
    """Days to wait before the next sprint load: 0, 2, 4, then weekly (never gives up)."""
    return 0 if attempts <= 0 else min(2 ** attempts, 7)


def _record_sprint_attempt(db, race_id, today):
    meta = get_or_create_meta(db, race_id)
    meta.sprint_attempts = (meta.sprint_attempts or 0) + 1
    meta.sprint_last_attempt = today.isoformat()


def _sprint_retry_due(meta, today) -> bool:
    if meta is None or not meta.sprint_last_attempt:
        return True
    last = datetime.date.fromisoformat(meta.sprint_last_attempt)
    return (today - last).days >= sprint_retry_delay_days(meta.sprint_attempts or 0)


def backfill_sprints(year, events, today=None) -> list:
    """Add sprint results to stored sprint-weekend races that don't have any yet.

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
            has_rows = db.query(SprintResult).filter(SprintResult.race_id == race.race_id).count() > 0
            if has_rows:
                continue
            meta = db.get(RaceMeta, race.race_id)
            if not _sprint_retry_due(meta, today):
                pending.append(event["name"])
                continue
            sprint_results = _load_sprint(year, event["round"])
            if not sprint_results:
                _record_sprint_attempt(db, race.race_id, today)
                db.commit()
                pending.append(event["name"])
                continue
            _add_sprint_rows(db, race.race_id, sprint_results)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Sprint backfill failed for {event['name']}: {e}")
            pending.append(event["name"])
        finally:
            db.close()
    return pending


def run_pipeline(year, race, has_sprint=False) -> bool:
    """Ingest one race (and its sprint) in a single transaction. Returns True on success.

    `race` may be a round number (preferred: FastF1 matches names fuzzily) or a name.
    Re-running replaces the race identified by (season, round) and keeps its race_id.
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
        lap_data = fetcher.get_lap_data(session)
        pitstop = fetcher.get_pitstop_data(session)
        race_info = fetcher.get_race_info(session)
        fastest_lap = fetcher.get_fastest_lap(session) or {}
        weather = fetcher.get_weather_data(session)

        # None = unavailable/not requested: leave any stored sprint rows untouched.
        sprint_results = _load_sprint(year, race) if has_sprint else None
        if has_sprint and sprint_results is None:
            print(f"Sprint data unavailable for {year} {race}; storing the race without it")

        # Optional enrichment: a failure here must never block the race itself.
        circuit_values = prepare_circuit_map(year, fetcher.get_circuit_key(session))

        db = SessionLocal()

        existing = (
            db.query(Race)
            .filter(Race.date.like(f"{year}-%"), Race.round == race_info["round"])
            .first()
        )
        race_id = None
        kept_sprint = []
        kept_circuit = None
        if existing:
            race_id = existing.race_id
            old_circuit = db.get(CircuitMap, race_id)
            if old_circuit is not None:
                kept_circuit = {c.name: getattr(old_circuit, c.name) for c in CircuitMap.__table__.columns if c.name != "race_id"}
                db.delete(old_circuit)
            if sprint_results is None:
                kept_sprint = [
                    {"position": r.position, "full_name": r.full_name, "team": r.team}
                    for r in db.query(SprintResult).filter(SprintResult.race_id == race_id)
                ]
            db.query(PitStop).filter(PitStop.race_id == race_id).delete()
            db.query(DriverResult).filter(DriverResult.race_id == race_id).delete()
            db.query(LapPosition).filter(LapPosition.race_id == race_id).delete()
            db.query(SprintResult).filter(SprintResult.race_id == race_id).delete()
            # summary is reset on re-ingest, so its prompt-version marker goes too
            db.query(RaceMeta).filter(RaceMeta.race_id == race_id).delete()
            db.delete(existing)
            db.flush()

        race_row = Race(
            race_id=race_id,  # reuse the old id so links and ordering stay stable
            name=race_info["name"],
            location=race_info["location"],
            date=race_info["date"],
            round=race_info["round"],
            total_laps=race_info["total_laps"],
            summary=None,
            fastest_lap_driver=fastest_lap.get("driver"),
            fastest_lap_time=fastest_lap.get("lap_time"),
            fastest_lap_number=fastest_lap.get("lap_number"),
            fastest_lap_team=fastest_lap.get("team"),
            air_temp=weather["air_temp"],
            track_temp=weather["track_temp"],
            rainfall="Yes" if weather["rainfall"] else "No",
        )
        db.add(race_row)
        db.flush()

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
            if position is None:
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
            ))

        for lap in lap_data:
            position = _to_int(lap["Position"])
            if position is None:
                continue
            db.add(LapPosition(
                race_id=race_row.race_id,
                driver=str(lap["Driver"]),
                lap_number=int(lap["LapNumber"]),
                position=position,
            ))

        # New lookup wins; if it could not run, keep what was stored before.
        stored_circuit = circuit_values or kept_circuit
        if stored_circuit:
            db.add(CircuitMap(race_id=race_row.race_id, **stored_circuit))

        _add_sprint_rows(db, race_row.race_id, sprint_results)
        if has_sprint and sprint_results is None and not kept_sprint:
            _record_sprint_attempt(db, race_row.race_id, datetime.date.today())
        for row in kept_sprint:
            db.add(SprintResult(race_id=race_row.race_id, **row))

        db.commit()
        return True

    except Exception as e:
        print(f"Pipeline failed for {year} {race}: {e}")
        if db:
            db.rollback()
        return False

    finally:
        if db:
            db.close()


def run_pending_races(year, today=None) -> list:
    """Fetch every completed race for the season that isn't in the DB yet.

    Returns the names of races that failed so the caller can exit non-zero.
    Missing sprint data is not a failure: it is retried here on every run and
    reported as a warning.
    """
    db = SessionLocal()
    try:
        existing_rounds = {
            r.round for r in db.query(Race).filter(Race.date.like(f"{year}-%")).all()
        }
    finally:
        db.close()

    failed = []
    events = fetcher.get_completed_races(year)
    for event in events:
        if event["round"] in existing_rounds:
            continue
        print(f"Fetching {event['name']} (round {event['round']})...")
        if not run_pipeline(year, event["round"], has_sprint=event["has_sprint"]):
            failed.append(event["name"])

    try:
        backfill_circuit_maps(today=today)
    except Exception as e:  # enrichment only: never fail the ingest run
        print(f"Circuit map backfill skipped: {e}")

    sprint_pending = backfill_sprints(year, events, today=today)
    if sprint_pending:
        print(f"Sprint results still unavailable for: {', '.join(sprint_pending)}")

    summarizer.backfill_summaries()
    return failed


if __name__ == "__main__":
    failed_races = run_pending_races(datetime.date.today().year)
    if failed_races:
        print(f"Failed races: {', '.join(failed_races)}")
        sys.exit(1)
