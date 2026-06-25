import fetcher
import summarizer
from database import SessionLocal
from models import Race
from models import DriverResult







def run_pipeline(year, race): 
    session = fetcher.load_session(year,race) 
    result = fetcher.get_race_results(session) 
    lap_data = fetcher.get_lap_data(session) 
    pitstop = fetcher.get_pitstop_data(session)   
    race_info = fetcher.get_race_info(session) 
    result_description = summarizer.format_result_for_prompt(result, race_info) 
    pitstop_description = summarizer.format_pitstops_for_prompt(race_info, pitstop)   
    
    db = SessionLocal() 
    race = Race(
        name = race_info["name"], 
        location=race_info["location"],
        date=race_info["date"],
        round=race_info["round"],
        total_laps=race_info["total_laps"],
        summary="TBD"
    )  
    db.add(race) 
    db.flush()    
    for driver in result: 
        dr = DriverResult(
            race_id = race.race_id, 
            position = int(driver["Position"]), 
            full_name = driver["FullName"], 
            team = driver["TeamName"], 
            time = driver["Time"],  


        ) 
        db.add(dr)
    db.commit()
    db.close()



    
    
if __name__ == "__main__":
    run_pipeline(2026, "Australia")
   

    





