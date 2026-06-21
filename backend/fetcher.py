import fastf1

fastf1.Cache.enable_cache("cache")

session = fastf1.get_session(2026, "Australia", "R")
session.load()

print("=== RACE RESULTS ===")
print(session.results[["Abbreviation", "FullName", "TeamName", "Position", "Time", "FastestLapTime"]].to_string())

print("\n=== LAP DATA (first 5 rows) ===")
laps = session.laps
print(laps[["Driver", "LapNumber", "LapTime", "Position", "Compound", "PitInTime", "PitOutTime"]].head(20).to_string())

print("\n=== PIT STOPS ===")
pit_laps = laps[laps["PitOutTime"].notna()][["Driver", "LapNumber", "Compound"]]
print(pit_laps.to_string())
