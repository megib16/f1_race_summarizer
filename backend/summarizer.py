
import fetcher 
import anthropic


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
        prompt = f"""You are an F1 race analyst. Write a concise 2-3 short to mid length paragraph race summary.
    Focus on the winner, key battles, strategy, and notable moments. Break the output into smaller paragraphs for readability. 

    {race_text}

    {pit_text}"""
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return next(block.text for block in message.content if block.type == "text")
    except Exception as e: 
        print(f"Failed to generate summary: {e}") 
    return None 
    



#Driver, LapNumber, Compound. Build a line for each one like: Russell pitted on lap 32 (Medium)  
if __name__ == "__main__":
    session = fetcher.load_session(2026, "Spain")
    results = fetcher.get_race_results(session)
    race_info = fetcher.get_race_info(session)
    pit_stops = fetcher.get_pitstop_data(session)

    print(format_result_for_prompt(results, race_info)) 
    print(format_pitstops_for_prompt(race_info, pit_stops)) 

          



