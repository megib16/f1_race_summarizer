import pytest

from standings import Classification, StandingsUnavailable, calculate_standings


def test_countback_uses_race_finishes_and_points_keep_fractional_awards():
    events = [
        Classification("2026-01-01", 1, False, "Alpha", "A", 1, 8, "Finished"),
        Classification("2026-01-01", 1, True, "Zulu", "Z", 1, 12.5, "Finished"),
        Classification("2026-01-01", 1, True, "Alpha", "A", 2, 4.5, "Finished"),
        Classification("2026-01-01", 1, True, "Excluded", "E", 3, 15, "Disqualified"),
    ]
    assert calculate_standings(events) == [
        {"full_name": "Zulu", "team": "Z", "points": 12.5},
        {"full_name": "Alpha", "team": "A", "points": 12.5},
        {"full_name": "Excluded", "team": "E", "points": 0},
    ]


def test_latest_event_team_wins_regardless_of_input_order():
    events = [
        Classification("2026-01-01", 1, True, "A", "New", 1, 25, "Finished"),
        Classification("2026-01-01", 1, False, "A", "Old", 1, 8, "Finished"),
    ]
    assert calculate_standings(events) == [{"full_name": "A", "team": "New", "points": 33}]


def test_missing_points_produce_a_domain_error_without_http_dependencies():
    with pytest.raises(StandingsUnavailable, match="source-awarded points"):
        calculate_standings([Classification("2026-01-01", 1, True, "A", "Team", 1, None, None)])
