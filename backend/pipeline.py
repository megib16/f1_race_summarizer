import fetcher 
import summarizer 

def run_pipeline(year, race): 
    session = fetcher.load_session(year,race) 
    result = fetcher.get_race_results(session) 
    lap_data = fetcher.get_lap_data(session) 
    pitstop = fetcher.get_pitstop_data(session)   
    race_info = fetcher.get_race_info(session) 
    result_description = summarizer.format_result_for_prompt(result, race_info) 
    pitstop_description = summarizer.format_pitstops_for_prompt(race_info, pitstop)   
    print(session) 
    print(result) 
    print(lap_data) 
    print(pitstop) 
    print(race_info) 
    print(result_description) 
    print(pitstop_description)  

    
    
if __name__ == "__main__":
    run_pipeline(2026, "Australia")
   

    


#Call fetcher.load_session(year, race) to get the session
#Call all the fetcher functions to get results, laps, pit stops, race info
#Call summarizer.generate_summary(...) to get the text summary
#Save everything to storage (we'll add this later — for now just print it)



