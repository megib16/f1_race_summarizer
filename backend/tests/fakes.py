"""Deterministic source data shared by unit and database integration tests."""



class FakeSession:
    pass


def install_fake_fetcher(monkeypatch, *, name="Test GP", date="2026-03-01", rnd=1,
                         results=None, fastest_lap="default", sprint="none"):
    """Replace every fetcher call used by run_pipeline so no FastF1/network is touched."""
    import fetcher

    f = fetcher
    results = results if results is not None else [
        {"Position": 1.0, "GridPosition": 2.0, "FullName": "A Driver", "TeamName": "Team A", "Abbreviation": "ADR", "Time": "t1"},
        {"Position": 2.0, "GridPosition": float("nan"), "FullName": "B Driver", "TeamName": "Team B", "Abbreviation": "BDR", "Time": "t2"},
    ]
    monkeypatch.setattr(f, "load_session", lambda y, r: FakeSession())
    monkeypatch.setattr(f, "get_race_results", lambda s: results)
    monkeypatch.setattr(f, "get_lap_data", lambda s: [
        {"Driver": "ADR", "LapNumber": 1, "Position": 1.0},
        {"Driver": "BDR", "LapNumber": 1, "Position": float("nan")},
    ])
    monkeypatch.setattr(f, "get_pitstop_data", lambda s: [
        {"Driver": "ADR", "LapNumber": 5, "OldCompound": "SOFT", "NewCompound": "HARD"},
    ])
    monkeypatch.setattr(f, "get_race_info", lambda s: {
        "name": name, "location": "Somewhere", "date": date, "round": rnd, "total_laps": 50,
    })
    monkeypatch.setattr(f, "get_fastest_lap", lambda s: (
        {"driver": "ADR", "lap_time": "x", "lap_number": 3, "team": "Team A"} if fastest_lap == "default" else fastest_lap
    ))
    monkeypatch.setattr(f, "get_weather_data", lambda s: {"air_temp": 20.0, "track_temp": 30.0, "rainfall": False})
    monkeypatch.setattr(f, "load_sprint_session", lambda y, r: FakeSession() if sprint != "unavailable" else None)
    monkeypatch.setattr(f, "get_sprint_results", lambda s: [
        {"Position": 1.0, "FullName": "A Driver", "TeamName": "Team A"},
        {"Position": 2.0, "FullName": "B Driver", "TeamName": "Team B"},
    ])


def square_outline(n_per_side=20, size=1000.0):
    """Closed-ish square loop, counter-clockwise from (0, 0)."""
    pts = []
    for i in range(n_per_side):
        pts.append((size * i / n_per_side, 0.0))
    for i in range(n_per_side):
        pts.append((size, size * i / n_per_side))
    for i in range(n_per_side):
        pts.append((size - size * i / n_per_side, size))
    for i in range(n_per_side):
        pts.append((0.0, size - size * i / n_per_side))
    return pts


def raw_payload(corners=None, rotation=0, outline=None):
    pts = outline or square_outline()
    return {
        "circuitName": "Test Circuit",
        "year": 2026,
        "rotation": rotation,
        "x": [p[0] for p in pts],
        "y": [p[1] for p in pts],
        "corners": corners if corners is not None else [
            {"number": 1, "trackPosition": {"x": 1000.0, "y": 0.0}, "angle": 0},   # index 20
            {"number": 2, "trackPosition": {"x": 1000.0, "y": 1000.0 - 50}, "angle": 90, "letter": "A"},
            {"number": 3, "trackPosition": {"x": 0.0, "y": 1000.0}, "angle": 180},
        ],
    }
