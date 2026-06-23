
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

if __name__ == "__main__":
    session = fetcher.load_session(2026, "Australia")
    results = fetcher.get_race_results(session)
    race_info = fetcher.get_race_info(session)
    pit_stops = fetcher.get_pitstop_data(session)

    print(format_result_for_prompt(results, race_info))


