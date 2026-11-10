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


def test_empty_weather_and_nonfinite_values_are_unknown():
    from types import SimpleNamespace
    session = SimpleNamespace(weather_data=pd.DataFrame())
    assert fetcher.get_weather_data(session) == {"air_temp": None, "track_temp": None, "rainfall": None}
    session.weather_data = pd.DataFrame({"AirTemp": [float("nan")], "TrackTemp": [float("inf")], "Rainfall": [None]})
    assert fetcher.get_weather_data(session) == {"air_temp": None, "track_temp": None, "rainfall": None}


def test_schedule_uses_the_supplied_date(monkeypatch):
    schedule = pd.DataFrame([
        {"RoundNumber": 1, "EventName": "GP1", "EventDate": pd.Timestamp("2026-03-01"), "EventFormat": "conventional"},
        {"RoundNumber": 2, "EventName": "GP2", "EventDate": pd.Timestamp("2026-03-08"), "EventFormat": "conventional"},
    ])
    monkeypatch.setattr(fetcher.fastf1, "get_event_schedule", lambda year: schedule)
    races = fetcher.get_completed_races(2026, today=datetime.date(2026, 3, 8))
    assert [r["round"] for r in races] == [1]
