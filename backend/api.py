import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json

from sqlalchemy import func

from database import SessionLocal
from models import Race, DriverResult, SprintResult, LapPosition, PitStop, CircuitMap

app = FastAPI()
POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
SPRINT_POINTS = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}

ALLOWED_ORIGINS = ["http://localhost:3000"]
if os.environ.get("FRONTEND_URL"):
    ALLOWED_ORIGINS.append(os.environ["FRONTEND_URL"].rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_race(db, race_id: int) -> Race:
    race = db.query(Race).filter(Race.race_id == race_id).first()
    if race is None:
        raise HTTPException(status_code=404, detail=f"Race {race_id} not found")
    return race


@app.get("/races")
def get_races(db=Depends(get_db)):
    # race_id order is insertion order, which is not chronological (a re-ingested
    # or backfilled race gets a later id), so never rely on it for "latest".
    races = db.query(Race).order_by(Race.date, Race.round, Race.race_id).all()
    return [
        {
            "race_id": r.race_id,
            "name": r.name,
            "location": r.location,
            "date": r.date,
            "round": r.round,
            "total_laps": r.total_laps,
            "summary": r.summary,
            "fastest_lap_driver": r.fastest_lap_driver,
            "fastest_lap_time": r.fastest_lap_time,
            "fastest_lap_number": r.fastest_lap_number,
            "fastest_lap_team": r.fastest_lap_team,
            "air_temp": r.air_temp,
            "track_temp": r.track_temp,
            "rainfall": r.rainfall,
        }
        for r in races
    ]


@app.get("/races/{race_id}/results")
def get_results(race_id: int, db=Depends(get_db)):
    require_race(db, race_id)
    results = (
        db.query(DriverResult)
        .filter(DriverResult.race_id == race_id)
        .order_by(DriverResult.position, DriverResult.driver_id)
        .all()
    )
    return [
        {
            "driver_id": r.driver_id,
            "race_id": r.race_id,
            "position": r.position,
            "grid_position": r.grid_position,
            "full_name": r.full_name,
            "abbreviation": r.abbreviation,
            "team": r.team,
            "time": r.time,
            "fastest_lap": r.fastest_lap,
        }
        for r in results
    ]


@app.get("/races/{race_id}/laps")
def get_laps(race_id: int, db=Depends(get_db)):
    require_race(db, race_id)
    laps = (
        db.query(LapPosition)
        .filter(LapPosition.race_id == race_id)
        .order_by(LapPosition.lap_number, LapPosition.position, LapPosition.driver)
        .all()
    )
    return [
        {
            "driver": l.driver,
            "lap_number": l.lap_number,
            "position": l.position,
        }
        for l in laps
    ]


@app.get("/races/{race_id}/pits")
def get_pitstops(race_id: int, db=Depends(get_db)):
    """Inferred pit-lane exits (lap_number is the out-lap), not measured stop durations."""
    require_race(db, race_id)
    pits = (
        db.query(PitStop)
        .filter(PitStop.race_id == race_id)
        .order_by(PitStop.lap_number, PitStop.driver, PitStop.id)
        .all()
    )
    return [
        {
            "driver": p.driver,
            "lap_number": p.lap_number,
            "old_compound": p.old_compound,
            "new_compound": p.new_compound,
        }
        for p in pits
    ]


@app.get("/races/{race_id}/circuit")
def get_circuit_map(race_id: int, db=Depends(get_db)):
    """Circuit outline and numbered corners for the race's season layout.

    Always one shape: `status` is "available" (with `map`) or "unavailable" (with a
    `reason`: not_fetched, no_data, invalid_outline, no_circuit_key). Geometry is
    approximate third-party data and contains no sector information.
    """
    require_race(db, race_id)
    row = db.get(CircuitMap, race_id)
    if row is None:
        return {"status": "unavailable", "reason": "not_fetched", "map": None}
    if row.status != "available" or not row.data:
        return {"status": "unavailable", "reason": row.reason or "no_data", "map": None}
    try:
        return {"status": "available", "reason": None, "map": json.loads(row.data), "source": row.source}
    except ValueError:
        return {"status": "unavailable", "reason": "corrupt_data", "map": None}


@app.get("/championship")
def get_championship(season: Optional[int] = None, through_round: Optional[int] = None, db=Depends(get_db)):
    """Driver standings for one season (default: the latest season in the DB).

    Races carry no year column, but `date` is always ISO `YYYY-MM-DD`, so the
    season is taken from its prefix. Points follow the 2026 rules: no fastest-lap
    point. `through_round` limits standings to rounds <= that round (standings
    "after round N"). Race and sprint results are filtered identically.
    Disqualifications and shortened-race half points are not modelled
    because no race status is stored.
    """
    if season is None:
        latest = db.query(func.max(Race.date)).scalar()
        if not latest:
            return []
        season = int(latest[:4])
    prefix = f"{season}-%"

    def in_scope(query):
        query = query.filter(Race.date.like(prefix))
        if through_round is not None:
            query = query.filter(Race.round <= through_round)
        return query

    # (date, round, 0=sprint/1=race) so the most recent team wins for drivers who switch.
    events = []
    race_rows = in_scope(
        db.query(DriverResult, Race.date, Race.round).join(Race, Race.race_id == DriverResult.race_id)
    ).all()
    for r, date, rnd in race_rows:
        events.append(((date, rnd or 0, 1), r.full_name, r.team, POINTS.get(r.position, 0)))
    sprint_rows = in_scope(
        db.query(SprintResult, Race.date, Race.round).join(Race, Race.race_id == SprintResult.race_id)
    ).all()
    for s, date, rnd in sprint_rows:
        events.append(((date, rnd or 0, 0), s.full_name, s.team, SPRINT_POINTS.get(s.position, 0)))

    totals: dict = {}
    for _, name, team, points in sorted(events, key=lambda e: e[0]):
        entry = totals.setdefault(name, {"full_name": name, "team": team, "points": 0})
        entry["team"] = team
        entry["points"] += points
    return sorted(totals.values(), key=lambda x: (-x["points"], x["full_name"]))
