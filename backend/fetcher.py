import fastf1
import os
import datetime

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

def get_completed_races(year: int) -> list[dict]:
    """Races in the season schedule whose race day has already passed.

    Compared by date only (not time) so a race that's still in progress
    today never gets fetched with partial results.
    """
    schedule = fastf1.get_event_schedule(year)
    today = datetime.date.today()
    races = []
    for _, event in schedule.iterrows():
        if int(event["RoundNumber"]) == 0:
            continue  # pre-season testing, not a race
        if event["EventDate"].date() >= today:
            continue
        races.append({
            "round": int(event["RoundNumber"]),
            "name": event["EventName"],
            "has_sprint": "sprint" in str(event["EventFormat"]).lower(),
        })
    return races

def load_session(year: int, race: str):
    try:
        session = fastf1.get_session(year, race, "R")
        session.load() 
        return session
 
    except Exception as e: 
        print(f"Failed to load seesion!: {e}")
    return None



def get_race_results(session) -> list[dict]:
    cols = ["Abbreviation", "FullName", "TeamName", "Position", "GridPosition", "Time"]
    if "FastestLapTime" in session.results.columns:
        cols.append("FastestLapTime")
    results = session.results[cols]
    return results.to_dict(orient="records")

def get_lap_data(session) -> list[dict]: 
    laps = session.laps[["Driver", "LapNumber", "LapTime", "Position", "Compound", "PitInTime", "PitOutTime"]] 
    return laps.to_dict(orient = "records") 

def get_fastest_lap(session) -> dict:
    try:
        laps = session.laps.pick_fastest()
        return {
            "driver": str(laps["Driver"]),
            "lap_time": str(laps["LapTime"]),
            "lap_number": int(laps["LapNumber"]), 
            "team": str(laps["Team"])
        } 
    except Exception as e: 
        print(f"No fastest lap recorded: {e}") 
        return None     
     
    

def _compound_name(value) -> str:
    if value is None or pd.isna(value):
        return "UNKNOWN"
    return str(value)


def get_pitstop_data(session) -> list[dict]:
    """Infer pit-lane exits from lap data.

    FastF1 sets PitOutTime on the *out-lap*, so `LapNumber` here is the first lap
    on the new tyres. A pit-out on a driver's first lap has no previous lap (pit
    lane start), so it is not an in-race stop and is skipped. Durations are not
    derived: this is only the compound change, not a measured stop time.
    """
    laps = session.laps.sort_values(["Driver", "LapNumber"])
    results = []
    for driver, driver_laps in laps.groupby("Driver", sort=True):
        previous = None
        for _, row in driver_laps.iterrows():
            compound = _compound_name(row["Compound"])
            if previous is not None and pd.notna(row["PitOutTime"]):
                results.append({
                    "Driver": driver,
                    "LapNumber": int(row["LapNumber"]),
                    "OldCompound": previous,
                    "NewCompound": compound,
                })
            previous = compound
    return results

def get_weather_data(session) -> dict:
    weather = session.weather_data
    return {
        "air_temp": round(float(weather["AirTemp"].mean()), 1),
        "track_temp": round(float(weather["TrackTemp"].mean()), 1),
        "rainfall": bool(weather["Rainfall"].any()),
    }

def load_sprint_session(year: int, race: str):
    try:
        session = fastf1.get_session(year, race, "S")
        session.load()
        return session
    except Exception as e:
        print(f"No sprint session for {race}: {e}")
    return None

def get_sprint_results(session) -> list[dict]:
    cols = ["FullName", "TeamName", "Position"]
    results = session.results[cols]
    return results.to_dict(orient="records")

def get_circuit_key(session):
    """FastF1/F1 live-timing circuit key for the session, or None if absent."""
    try:
        return int(session.session_info["Meeting"]["Circuit"]["Key"])
    except Exception:
        return None


def load_session_info(year: int, race):
    """A session with only event/session info loaded (no laps or telemetry): cheap lookups."""
    session = fastf1.get_session(year, race, "R")
    session.load(laps=False, telemetry=False, weather=False, messages=False)
    return session


def fetch_circuit_payload(year: int, circuit_key: int):
    """Raw MultiViewer circuit payload (outline, corners, rotation) or None if it has none.

    FastF1's public `get_circuit_info` discards the outline, so this uses its own
    request helper (`fastf1.mvapi.api`, an internal module: fastf1 is pinned in
    requirements.txt). Network errors propagate so callers can tell "no data"
    (None) from "could not ask".
    """
    from fastf1.mvapi.api import get_circuit
    return get_circuit(year=year, circuit_key=circuit_key)


def get_race_info(session) -> dict:
    event = session.event
    return {
        "name": event["EventName"],
        "location": event["Location"],
        "date": str(event["EventDate"].date()),
        "round": int(event["RoundNumber"]),
        "total_laps": int(session.laps["LapNumber"].max()),
    }

























