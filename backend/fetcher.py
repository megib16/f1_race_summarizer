import fastf1

fastf1.Cache.enable_cache("cache")

def load_session(year: int, race: str):
    session = fastf1.get_session(year, race, "R")
    session.load()
    return session


def get_race_results(session) -> list[dict]: 
    results = session.results[["Abbreviation", "FullName", "TeamName", "Position", "Time"]] 
    return results.to_dict(orient = "records")

def get_lap_data(session) -> list[dict]: 
    laps = session.laps[["Driver", "LapNumber", "LapTime", "Position", "Compound", "PitInTime", "PitOutTime"]] 
    return laps.to_dict(orient = "records") 

def get_pitstop_data(session) -> list[dict]:
    laps = session.laps
    pitstop = laps[laps["PitOutTime"].notna()][["Driver", "LapNumber", "Compound"]]
    return pitstop.to_dict(orient="records")

def get_race_info(session) -> dict:
    event = session.event
    return {
        "name": event["EventName"],
        "location": event["Location"],
        "date": str(event["EventDate"].date()),
        "round": int(event["RoundNumber"]),
        "total_laps": int(session.laps["LapNumber"].max()),
    }

























