from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal
from models import Race, DriverResult

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/races")
def get_races():
    db = SessionLocal()
    races = db.query(Race).all()
    db.close()
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
def get_results(race_id: int):
    db = SessionLocal()
    results = db.query(DriverResult).filter(DriverResult.race_id == race_id).all()
    db.close()
    return [
        {
            "driver_id": r.driver_id,
            "race_id": r.race_id,
            "position": r.position,
            "full_name": r.full_name,
            "team": r.team,
            "time": r.time,
            "fastest_lap": r.fastest_lap,
        }
        for r in results
    ]

@app.get("/races/{race_id}/laps")
def get_laps(race_id: int):
    from models import LapPosition
    db = SessionLocal()
    laps = db.query(LapPosition).filter(LapPosition.race_id == race_id).all()
    db.close()
    return [
        {
            "driver": l.driver,
            "lap_number": l.lap_number,
            "position": l.position,
        }
        for l in laps
    ] 

@app.get("/races/{race_id}/pits") 
def get_pitstops(race_id: int): 
   from models import PitStop
   db = SessionLocal() 
   pits = db.query(PitStop).filter(PitStop.race_id == race_id).all() 
   db.close() 
   return [
       {
           "driver": p.driver,
            "lap_number": p.lap_number,
            "old_compound": p.old_compound, 
            "new_compound": p.new_compound
       } 
       for p in pits
   ]


