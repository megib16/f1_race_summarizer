import summarizer


def test_format_result_for_prompt_lists_drivers_in_order():
    race_info = {"name": "Spanish Grand Prix", "date": "2026-09-13", "total_laps": 57}
    results = [
        {"Position": "1", "FullName": "Kimi Antonelli", "TeamName": "Mercedes", "Time": "1:34:23.754"},
        {"Position": "2", "FullName": "Max Verstappen", "TeamName": "Red Bull Racing", "Time": "+4.351s"},
    ]

    text = summarizer.format_result_for_prompt(results, race_info)

    assert "Spanish Grand Prix 2026-09-13" in text
    assert "Total laps: 57" in text
    assert "P1: Kimi Antonelli (Mercedes) - 1:34:23.754" in text
    assert "P2: Max Verstappen (Red Bull Racing) - +4.351s" in text


def test_format_pitstops_for_prompt_sorts_by_lap():
    race_info = {"name": "Spanish Grand Prix"}
    pit_stops = [
        {"Driver": "VER", "LapNumber": 30, "NewCompound": "HARD"},
        {"Driver": "ANT", "LapNumber": 15, "NewCompound": "HARD"},
    ]

    text = summarizer.format_pitstops_for_prompt(race_info, pit_stops)
    lines = text.splitlines()

    assert lines.index("ANT pitted on lap 15 (HARD)") < lines.index("VER pitted on lap 30 (HARD)")


def test_generate_summary_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = summarizer.generate_summary(
        race_info={"name": "Test GP", "date": "2026-01-01", "total_laps": 10},
        results=[{"Position": "1", "FullName": "A Driver", "TeamName": "A Team", "Time": "1:00:00"}],
        pit_stops=[],
    )

    assert result is None
