import fetcher
import summarizer
from database import SessionLocal
from models import Race, DriverResult, LapPosition, PitStop 



def run_pipeline(year, race):
    session = fetcher.load_session(year, race)
    result = fetcher.get_race_results(session)
    lap_data = fetcher.get_lap_data(session)
    pitstop = fetcher.get_pitstop_data(session)
    race_info = fetcher.get_race_info(session)
    fastest_lap = fetcher.get_fastest_lap(session)
    weather = fetcher.get_weather_data(session)
    result_description = summarizer.format_result_for_prompt(result, race_info)
    pitstop_description = summarizer.format_pitstops_for_prompt(race_info, pitstop)

    db = SessionLocal()
    race_row = Race(
        name=race_info["name"],
        location=race_info["location"],
        date=race_info["date"],
        round=race_info["round"],
        total_laps=race_info["total_laps"],
        summary= summarizer.generate_summary(race_info, result, pitstop) ,
        fastest_lap_driver=fastest_lap["driver"],
        fastest_lap_time=fastest_lap["lap_time"],
        fastest_lap_number=fastest_lap["lap_number"], 
        fastest_lap_team=fastest_lap["team"], 
        air_temp=weather["air_temp"],
        track_temp=weather["track_temp"],
        rainfall="Yes" if weather["rainfall"] else "No",
    )
    db.add(race_row)
    db.flush() 

    for pit in pitstop: 
        ps = PitStop(
            race_id = race_row.race_id, 
            driver = pit["Driver"], 
            lap_number = int(pit["LapNumber"]), 
            old_compound = pit["OldCompound"],
            new_compound = pit["NewCompound"], 
        ) 
        db.add(ps) 

    for driver in result:
        dr = DriverResult(
            race_id=race_row.race_id,
            position=int(driver["Position"]),
            full_name=driver["FullName"],
            team=driver["TeamName"],
            time=str(driver["Time"]),
            fastest_lap=str(driver.get("FastestLapTime", "")),
        )
        db.add(dr)

    for lap in lap_data:
        if lap["Position"] is None or str(lap["Position"]) == "nan":
            continue
        lp = LapPosition(
            race_id=race_row.race_id,
            driver=str(lap["Driver"]),
            lap_number=int(lap["LapNumber"]),
            position=int(lap["Position"]),
        )
        db.add(lp)

    db.commit()
    db.close()


if __name__ == "__main__":
    run_pipeline(2026, "Australia")
