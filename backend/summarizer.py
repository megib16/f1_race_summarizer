
import fetcher
import anthropic
from database import SessionLocal
from models import Race, DriverResult, PitStop


def format_result_for_prompt(results, race_info): 
    lines = [] 
    lines.append(f"Race: {race_info['name']} {race_info['date']}") 
    lines.append(f"Total laps: {race_info['total_laps']}")
    lines.append("")
    
    for driver in results:
        position = int(driver["Position"])
        name = driver["FullName"]
        team = driver["TeamName"]
        time = driver["Time"]
        lines.append(f"P{position}: {name} ({team}) - {time}")
    
    return "\n".join(lines) 


def format_pitstops_for_prompt(race_info, pit_stops): 
    lines = [] 
    lines.append(f" {race_info['name']} Pit stop information") 
    lines.append("") 
    sorted_pitstops = sorted(pit_stops, key = lambda x: x["LapNumber"])
    for lap in sorted_pitstops: 
            name = lap["Driver"]
            lap_number = lap["LapNumber"]  
            compound = lap["NewCompound"]
            lines.append(f"{name} pitted on lap {lap_number} ({compound})") 
    return "\n".join(lines) 

def generate_summary(race_info, results, pit_stops) -> str:
    try:
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        race_text = format_result_for_prompt(results, race_info)
        pit_text = format_pitstops_for_prompt(race_info, pit_stops)
        prompt = f"""You are an F1 race analyst. Keep it concise, maximum of three short to mid length paragraphs. 
                     Focus on the winner, key battles, strategy, and notable moments. Break the output into smaller paragraphs for readability. 
                     Add a creative title resembing ones from articles or newspapers. Limit the usage of em dashes. 
                     Keep the choice of words in the summary simple and understandable for the everyday reader, without compromising on information.  

    {race_text}

    {pit_text}"""
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        return next(block.text for block in message.content if block.type == "text")
    except Exception as e:
        print(f"Failed to generate summary: {e}")
    return None


def backfill_summaries():
    """Generate summaries for any races missing one, without re-fetching FastF1 data.

    Decoupled from run_pipeline so a slow/failing Claude API call never blocks
    or rolls back the race data ingestion, and can be safely retried on its own.
    """
    db = SessionLocal()
    try:
        races = db.query(Race).filter(Race.summary.is_(None)).all()
        for race in races:
            race_info = {
                "name": race.name,
                "date": race.date,
                "total_laps": race.total_laps,
            }
            results = [
                {
                    "Position": r.position,
                    "FullName": r.full_name,
                    "TeamName": r.team,
                    "Time": r.time,
                }
                for r in db.query(DriverResult).filter(DriverResult.race_id == race.race_id).all()
            ]
            pit_stops = [
                {
                    "Driver": p.driver,
                    "LapNumber": p.lap_number,
                    "NewCompound": p.new_compound,
                }
                for p in db.query(PitStop).filter(PitStop.race_id == race.race_id).all()
            ]

            summary = generate_summary(race_info, results, pit_stops)
            if summary:
                race.summary = summary
                db.commit()
            else:
                print(f"Skipping {race.name}: summary generation failed, will retry next run")
    finally:
        db.close()





#Driver, LapNumber, Compound. Build a line for each one like: Russell pitted on lap 32 (Medium)  
if __name__ == "__main__":
    session = fetcher.load_session(2026, "Spain")
    results = fetcher.get_race_results(session)
    race_info = fetcher.get_race_info(session)
    pit_stops = fetcher.get_pitstop_data(session)

    print(format_result_for_prompt(results, race_info)) 
    print(format_pitstops_for_prompt(race_info, pit_stops)) 

          



