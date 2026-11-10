"""Transactional ingestion writes. Callers own commit/rollback; no network I/O here."""
from datetime import date

from sqlalchemy.orm import Session

from ingest_data import RacePayload, SprintPayload
from models import Race, DriverResult, LapPosition, PitStop, SprintResult, RaceMeta, CircuitMap, IngestState, get_or_create_meta

OPTIONAL_FACTS = frozenset({
    "air_temp", "track_temp", "rainfall", "fastest_lap_driver", "fastest_lap_time",
    "fastest_lap_number", "fastest_lap_team",
})


def record_sprint_attempt(db: Session, race_id: int, today: date) -> None:
    meta = get_or_create_meta(db, race_id)
    meta.sprint_attempts = (meta.sprint_attempts or 0) + 1
    meta.sprint_last_attempt = today.isoformat()


def replace_sprint(db: Session, race_id: int, payload: SprintPayload | None, state: IngestState, today: date) -> bool:
    state.sprint_required = True
    old_count = db.query(SprintResult).filter_by(race_id=race_id).count()
    if payload is None or not payload.results or len(payload.results) < old_count:
        record_sprint_attempt(db, race_id, today)
        return False
    db.query(SprintResult).filter_by(race_id=race_id).delete()
    db.add_all([SprintResult(race_id=race_id, **row.model_dump()) for row in payload.results])
    state.sprint_refreshed_at = today.isoformat()
    state.sprint_complete = payload.complete
    if not payload.complete:
        record_sprint_attempt(db, race_id, today)
    else:
        meta = db.get(RaceMeta, race_id)
        if meta:
            meta.sprint_attempts = 0
            meta.sprint_last_attempt = None
    return payload.complete


def store_circuit(db: Session, race_id: int, values: dict | None) -> None:
    if values is None:
        return
    row = db.get(CircuitMap, race_id)
    if row is None:
        row = CircuitMap(race_id=race_id)
        db.add(row)
    if row.status != "available" or values["status"] == "available":
        for key, value in values.items():
            setattr(row, key, value)


def store_race(db: Session, *, year: int, payload: RacePayload, circuit: dict | None,
               sprint: SprintPayload | None, has_sprint: bool, sprint_attempted: bool, today: date) -> int:
    existing = db.query(Race).filter(
        Race.date.like(f"{year}-%"), Race.round == payload.fields.round
    ).with_for_update().first()
    race = existing or Race()
    if existing:
        if db.query(LapPosition).filter_by(race_id=race.race_id).count() > len(payload.laps):
            raise ValueError("Refusing to replace fuller lap data with partial data")
        if db.query(DriverResult).filter_by(race_id=race.race_id).count() > len(payload.results):
            raise ValueError("Refusing to replace a fuller classification with partial results")
    for key, value in payload.fields.model_dump().items():
        if existing and value is None and key in OPTIONAL_FACTS:
            continue
        setattr(race, key, value)
    db.add(race)
    db.flush()
    for model, rows in ((PitStop, payload.pits), (DriverResult, payload.results), (LapPosition, payload.laps)):
        db.query(model).filter(model.race_id == race.race_id).delete()
        db.add_all([model(race_id=race.race_id, **row.model_dump()) for row in rows])
    store_circuit(db, race.race_id, circuit)
    state = db.get(IngestState, race.race_id)
    if state is None:
        state = IngestState(race_id=race.race_id)
        db.add(state)
    state.race_refreshed_at = today.isoformat()
    state.race_complete = payload.complete
    if has_sprint:
        state.sprint_required = True
        if sprint_attempted:
            replace_sprint(db, race.race_id, sprint, state, today)
    return race.race_id
