from types import SimpleNamespace

import pandas as pd

import fetcher


def make_session(rows):
    return SimpleNamespace(laps=pd.DataFrame(rows, columns=["Driver", "LapNumber", "Compound", "PitOutTime"]))


def test_pitstop_is_the_out_lap_with_previous_compound():
    session = make_session([
        ("VER", 1, "MEDIUM", pd.NaT),
        ("VER", 2, "MEDIUM", pd.NaT),
        ("VER", 3, "HARD", pd.Timedelta(minutes=5)),
        ("VER", 4, "HARD", pd.NaT),
    ])

    assert fetcher.get_pitstop_data(session) == [
        {"Driver": "VER", "LapNumber": 3, "OldCompound": "MEDIUM", "NewCompound": "HARD"},
    ]


def test_first_lap_pit_out_is_not_a_stop():
    session = make_session([
        ("HAM", 1, "HARD", pd.Timedelta(minutes=1)),  # pit lane start
        ("HAM", 2, "HARD", pd.NaT),
    ])

    assert fetcher.get_pitstop_data(session) == []


def test_missing_compound_becomes_unknown_not_string_nan():
    session = make_session([
        ("NOR", 1, None, pd.NaT),
        ("NOR", 2, float("nan"), pd.Timedelta(minutes=2)),
    ])

    stops = fetcher.get_pitstop_data(session)

    assert stops == [{"Driver": "NOR", "LapNumber": 2, "OldCompound": "UNKNOWN", "NewCompound": "UNKNOWN"}]


def test_stops_are_grouped_per_driver_even_if_laps_are_interleaved():
    session = make_session([
        ("B", 2, "HARD", pd.Timedelta(minutes=1)),
        ("A", 1, "SOFT", pd.NaT),
        ("B", 1, "SOFT", pd.NaT),
        ("A", 2, "MEDIUM", pd.Timedelta(minutes=1)),
    ])

    stops = fetcher.get_pitstop_data(session)

    assert [(s["Driver"], s["OldCompound"], s["NewCompound"]) for s in stops] == [
        ("A", "SOFT", "MEDIUM"),
        ("B", "SOFT", "HARD"),
    ]
