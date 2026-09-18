import datetime

import pandas as pd

import fetcher


def test_get_completed_races_filters_future_and_testing(monkeypatch):
    today = datetime.date.today()
    schedule = pd.DataFrame([
        {"RoundNumber": 0, "EventName": "Pre-Season Testing", "EventDate": pd.Timestamp(today - datetime.timedelta(days=30)), "EventFormat": "testing"},
        {"RoundNumber": 1, "EventName": "Past Grand Prix", "EventDate": pd.Timestamp(today - datetime.timedelta(days=7)), "EventFormat": "conventional"},
        {"RoundNumber": 2, "EventName": "Past Sprint Grand Prix", "EventDate": pd.Timestamp(today - datetime.timedelta(days=1)), "EventFormat": "sprint_qualifying"},
        {"RoundNumber": 3, "EventName": "Future Grand Prix", "EventDate": pd.Timestamp(today + datetime.timedelta(days=7)), "EventFormat": "conventional"},
    ])
    monkeypatch.setattr(fetcher.fastf1, "get_event_schedule", lambda year: schedule)

    races = fetcher.get_completed_races(2026)

    assert [r["round"] for r in races] == [1, 2]
    assert races[0]["has_sprint"] is False
    assert races[1]["has_sprint"] is True
