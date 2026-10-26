
import os
import re

import fetcher
import anthropic
from database import SessionLocal
from models import Race, DriverResult, PitStop, RaceMeta, get_or_create_meta


# Bump whenever the prompt changes so summaries written under older prompts can be found.
# Version 1 is implicit: summaries with no race_meta row predate version tracking.
PROMPT_VERSION = 2
SUMMARY_MODEL = os.environ.get("SUMMARY_MODEL", "claude-sonnet-5")

_TIMEDELTA = re.compile(r"(\d+) days (\d+):(\d+):(\d+)(?:\.(\d+))?")
_MISSING = {"", "NaT", "None", "nan"}


def _clean_time(value) -> str:
    """Readable time for the prompt. pandas Timedelta strings are converted; unknown stays unknown."""
    text = "" if value is None else str(value)
    if text in _MISSING:
        return "no time recorded"
    match = _TIMEDELTA.match(text)
    if not match:
        return text
    _, h, m, sec, frac = match.groups()
    frac = (frac or "0").ljust(3, "0")[:3]
    h, m, sec = int(h), int(m), int(sec)
    return f"{h}:{m:02d}:{sec:02d}.{frac}" if h else f"{m}:{sec:02d}.{frac}"


def format_result_for_prompt(results, race_info):
    lines = []
    lines.append(f"Race: {race_info['name']} {race_info['date']}")
    lines.append(f"Total laps: {race_info['total_laps']}")
    lines.append("")

    for driver in results:
        position = int(driver["Position"])
        line = f"P{position}: {driver['FullName']} ({driver['TeamName']}) - {_clean_time(driver['Time'])}"
        grid = driver.get("GridPosition")
        if grid is not None and int(grid) >= 1:
            line += f" [started P{int(grid)}]"
        lines.append(line)

    return "\n".join(lines)


def format_pitstops_for_prompt(race_info, pit_stops):
    lines = []
    lines.append(f" {race_info['name']} Pit stop information")
    lines.append("")
    sorted_pitstops = sorted(pit_stops, key=lambda x: x["LapNumber"])
    for lap in sorted_pitstops:
        lines.append(f"{lap['Driver']} left the pits on lap {lap['LapNumber']} on {lap['NewCompound']} tyres")
    return "\n".join(lines)


def format_facts_for_prompt(race_info) -> str:
    """Weather and fastest-lap facts, only the ones actually available."""
    lines = []
    if race_info.get("location"):
        lines.append(f"Location: {race_info['location']}")
    if race_info.get("air_temp") is not None and race_info.get("track_temp") is not None:
        lines.append(
            f"Session average air temperature {race_info['air_temp']}C, track temperature {race_info['track_temp']}C"
        )
    if race_info.get("rainfall"):
        lines.append(f"Rain recorded during the session: {race_info['rainfall']}")
    if race_info.get("fastest_lap_driver") and race_info.get("fastest_lap_time"):
        fl = (
            f"Fastest lap: {race_info['fastest_lap_driver']} "
            f"{_clean_time(race_info['fastest_lap_time'])}"
        )
        if race_info.get("fastest_lap_number"):
            fl += f" on lap {race_info['fastest_lap_number']}"
        lines.append(fl)
    return "\n".join(lines)


GROUNDING_RULES = """You are an F1 race writer. Write ONLY from the data below.
Rules:
- Use only facts stated in the data. Do not invent or imply overtakes, battles, crashes, safety cars, penalties, mechanical problems, team radio, driver quotes or reasons for any result.
- A missing time means no time was recorded. Do not say why (do not call it a retirement or crash).
- Tyre information lists pit-lane exits and the tyre fitted afterwards. It does not include stop durations or reasons, so do not describe stop speed or strategy intent.
- If the data is thin, write a shorter summary instead of filling space.
Style: a creative newspaper-style title, then at most three short paragraphs in plain, simple English. Limit em dashes."""


def build_prompt(race_info, results, pit_stops) -> str:
    parts = [GROUNDING_RULES, "", format_result_for_prompt(results, race_info)]
    facts = format_facts_for_prompt(race_info)
    if facts:
        parts += ["", facts]
    parts += ["", format_pitstops_for_prompt(race_info, pit_stops)]
    return "\n".join(parts)


def generate_summary(race_info, results, pit_stops):
    """A summary grounded in the supplied data, or None on any failure (callers retry later)."""
    if not results:
        return None
    try:
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        message = client.messages.create(
            model=SUMMARY_MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": build_prompt(race_info, results, pit_stops)}],
        )
        text = next((block.text for block in message.content if block.type == "text"), "")
        return text.strip() or None
    except Exception as e:
        print(f"Failed to generate summary: {e}")
    return None


def _summary_inputs(db, race):
    race_info = {
        "name": race.name,
        "date": race.date,
        "total_laps": race.total_laps,
        "location": race.location,
        "air_temp": race.air_temp,
        "track_temp": race.track_temp,
        "rainfall": race.rainfall,
        "fastest_lap_driver": race.fastest_lap_driver,
        "fastest_lap_time": race.fastest_lap_time,
        "fastest_lap_number": race.fastest_lap_number,
    }
    results = [
        {
            "Position": r.position,
            "FullName": r.full_name,
            "TeamName": r.team,
            "Time": r.time,
            "GridPosition": r.grid_position,
        }
        for r in db.query(DriverResult)
        .filter(DriverResult.race_id == race.race_id)
        .order_by(DriverResult.position)
    ]
    pit_stops = [
        {"Driver": p.driver, "LapNumber": p.lap_number, "NewCompound": p.new_compound}
        for p in db.query(PitStop).filter(PitStop.race_id == race.race_id).order_by(PitStop.lap_number)
    ]
    return race_info, results, pit_stops


def _save_summary(db, race, summary):
    race.summary = summary
    get_or_create_meta(db, race.race_id).summary_prompt_version = PROMPT_VERSION
    db.commit()


def backfill_summaries():
    """Generate summaries for any races missing one, without re-fetching FastF1 data.

    A failed generation leaves the summary NULL, so the race is retried next run.
    """
    db = SessionLocal()
    try:
        races = db.query(Race).filter(Race.summary.is_(None)).all()
        for race in races:
            summary = generate_summary(*_summary_inputs(db, race))
            if summary:
                _save_summary(db, race, summary)
            else:
                print(f"Skipping {race.name}: summary generation failed, will retry next run")
    finally:
        db.close()


def find_stale_summaries(db):
    """Races whose existing summary was written under an older prompt (or before versions were tracked)."""
    races = db.query(Race).filter(Race.summary.isnot(None)).order_by(Race.date, Race.round).all()
    stale = []
    for race in races:
        meta = db.get(RaceMeta, race.race_id)
        version = (meta.summary_prompt_version if meta else None) or 1
        if version < PROMPT_VERSION:
            stale.append((race, version))
    return stale


def regenerate_stale_summaries(race_ids=None, limit=None):
    """Regenerate stale summaries in place. Makes live model calls: callers must opt in.

    The old summary is only replaced after a new one is generated successfully, so a
    failure keeps the old text and the race stays stale (and therefore retryable).
    Returns (regenerated, failed) lists of race names.
    """
    db = SessionLocal()
    regenerated, failed = [], []
    try:
        targets = [race for race, _ in find_stale_summaries(db)]
        if race_ids is not None:
            targets = [r for r in targets if r.race_id in set(race_ids)]
        if limit is not None:
            targets = targets[:limit]
        for race in targets:
            summary = generate_summary(*_summary_inputs(db, race))
            if summary:
                _save_summary(db, race, summary)
                regenerated.append(race.name)
            else:
                failed.append(race.name)
    finally:
        db.close()
    return regenerated, failed


#Driver, LapNumber, Compound. Build a line for each one like: Russell pitted on lap 32 (Medium)  
if __name__ == "__main__":
    session = fetcher.load_session(2026, "Spain")
    results = fetcher.get_race_results(session)
    race_info = fetcher.get_race_info(session)
    pit_stops = fetcher.get_pitstop_data(session)

    print(format_result_for_prompt(results, race_info)) 
    print(format_pitstops_for_prompt(race_info, pit_stops)) 

          



