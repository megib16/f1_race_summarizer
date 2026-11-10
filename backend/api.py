import os
from typing import Optional, Annotated
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Path
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal, engine
from migrate import check_schema
from security import RateLimiter
from schemas import CircuitData
from pydantic import ValidationError
from data_utils import finite_number
from standings import Classification, StandingsUnavailable, calculate_standings
from models import Race, DriverResult, SprintResult, LapPosition, PitStop, CircuitMap, IngestState

@asynccontextmanager
async def lifespan(app):
    check_schema(engine)
    yield


app = FastAPI(lifespan=lifespan)
limiter = RateLimiter(int(os.environ.get("API_REQUESTS_PER_MINUTE", "120")))


@app.middleware("http")
async def protect_requests(request: Request, call_next):
    if request.method == "GET" and request.url.path != "/health":
        key = request.client.host if request.client else "unknown"
        if not limiter.allow(key):
            return JSONResponse({"detail": "Too many requests"}, status_code=429, headers={"Retry-After": "60"})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.method == "GET" and response.status_code == 200 and request.url.path != "/health":
        response.headers["Cache-Control"] = "public, max-age=60"
    return response


@app.get("/health")
def health():
    # Startup checks schema compatibility; readiness also verifies connectivity.
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return {"status": "ok"}

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
def get_races(db=Depends(get_db), limit: Annotated[int, Query(ge=1, le=500)] = 500,
              offset: Annotated[int, Query(ge=0, le=1000000)] = 0):
    # race_id order is insertion order, which is not chronological (a re-ingested
    # or backfilled race gets a later id), so never rely on it for "latest".
    races = db.query(Race).order_by(Race.date, Race.round, Race.race_id).offset(offset).limit(limit).all()
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
            "air_temp": finite_number(r.air_temp),
            "track_temp": finite_number(r.track_temp),
            "rainfall": r.rainfall,
        }
        for r in races
    ]


@app.get("/races/{race_id}/results")
def get_results(race_id: Annotated[int, Path(ge=1, le=2147483647)], db=Depends(get_db)):
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
            "status": r.status,
            "points": finite_number(r.points),
        }
        for r in results
    ]


@app.get("/races/{race_id}/laps")
def get_laps(race_id: Annotated[int, Path(ge=1, le=2147483647)], db=Depends(get_db),
             limit: Annotated[int, Query(ge=1, le=10000)] = 10000,
             offset: Annotated[int, Query(ge=0, le=1000000)] = 0):
    require_race(db, race_id)
    laps = (
        db.query(LapPosition)
        .filter(LapPosition.race_id == race_id)
        .order_by(LapPosition.lap_number, LapPosition.position, LapPosition.driver)
        .offset(offset).limit(limit).all()
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
def get_pitstops(race_id: Annotated[int, Path(ge=1, le=2147483647)], db=Depends(get_db)):
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
def get_circuit_map(race_id: Annotated[int, Path(ge=1, le=2147483647)], db=Depends(get_db)):
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
        return {"status": "available", "reason": None, "map": CircuitData.model_validate_json(row.data).model_dump(mode="json"), "source": row.source}
    except (ValueError, ValidationError):
        return {"status": "unavailable", "reason": "corrupt_data", "map": None}


@app.get("/championship")
def get_championship(season: Annotated[Optional[int], Query(ge=1950, le=2100)] = None, through_round: Annotated[Optional[int], Query(ge=0, le=100)] = None, db=Depends(get_db)):
    """Standings use source-awarded points, including shortened races and penalties.

    Legacy rows without awarded points require re-ingestion rather than guessed scoring.
    Equal points use race finishing-position countback, then name if still tied.
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

    states = in_scope(db.query(IngestState).join(Race, Race.race_id == IngestState.race_id)).all()
    if any(not s.race_complete or (s.sprint_required and not s.sprint_complete) for s in states):
        raise HTTPException(status_code=409, detail="Standings are waiting for complete race and sprint classifications")

    # (date, round, 0=sprint/1=race) so the most recent team wins for drivers who switch.
    events = []
    race_rows = in_scope(
        db.query(DriverResult, Race.date, Race.round).join(Race, Race.race_id == DriverResult.race_id)
    ).all()
    for r, date, rnd in race_rows:
        events.append(Classification(
            date=date, round=rnd or 0, is_race=True, full_name=r.full_name,
            team=r.team, position=r.position, points=r.points, status=r.status,
        ))
    sprint_rows = in_scope(
        db.query(SprintResult, Race.date, Race.round).join(Race, Race.race_id == SprintResult.race_id)
    ).all()
    for s, date, rnd in sprint_rows:
        events.append(Classification(
            date=date, round=rnd or 0, is_race=False, full_name=s.full_name,
            team=s.team, position=s.position, points=s.points, status=s.status,
        ))

    try:
        return calculate_standings(events)
    except StandingsUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
