import fastf1
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fastf1.Cache.enable_cache(os.path.join(BASE_DIR, "cache"))

def load_session(year: int, race: str):
    session = fastf1.get_session(year, race, "R")
    session.load()
    return session


def get_race_results(session) -> list[dict]:
    cols = ["Abbreviation", "FullName", "TeamName", "Position", "Time"]
    if "FastestLapTime" in session.results.columns:
        cols.append("FastestLapTime")
    results = session.results[cols]
    return results.to_dict(orient="records")

def get_lap_data(session) -> list[dict]: 
    laps = session.laps[["Driver", "LapNumber", "LapTime", "Position", "Compound", "PitInTime", "PitOutTime"]] 
    return laps.to_dict(orient = "records") 

def get_fastest_lap(session) -> dict:
    laps = session.laps.pick_fastest()
    return {
        "driver": str(laps["Driver"]),
        "lap_time": str(laps["LapTime"]),
        "lap_number": int(laps["LapNumber"]), 
        "team": str(laps["Team"])
    }

def get_pitstop_data(session) -> list[dict]:
    laps = session.laps.sort_values(["Driver", "LapNumber"])
    pit_laps = laps[laps["PitOutTime"].notna()]
    results = []
    for _, row in pit_laps.iterrows():
        driver = row["Driver"]
        lap_num = row["LapNumber"]
        prev = laps[(laps["Driver"] == driver) & (laps["LapNumber"] < lap_num)]
        old = str(prev.iloc[-1]["Compound"]) if len(prev) > 0 else ""
        results.append({
            "Driver": driver,
            "LapNumber": int(lap_num),
            "OldCompound": old,
            "NewCompound": str(row["Compound"]),
        })
    return results

def get_weather_data(session) -> dict:
    weather = session.weather_data
    return {
        "air_temp": round(float(weather["AirTemp"].mean()), 1),
        "track_temp": round(float(weather["TrackTemp"].mean()), 1),
        "rainfall": bool(weather["Rainfall"].any()),
    }

def get_race_info(session) -> dict:
    event = session.event
    return {
        "name": event["EventName"],
        "location": event["Location"],
        "date": str(event["EventDate"].date()),
        "round": int(event["RoundNumber"]),
        "total_laps": int(session.laps["LapNumber"].max()),
    }

























