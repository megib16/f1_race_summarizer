import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import api
from models import Base, Race, DriverResult, SprintResult, LapPosition, PitStop


@pytest.fixture
def db():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def add_race(db, race_id, name, date, rnd):
    db.add(Race(race_id=race_id, name=name, date=date, round=rnd))
    db.commit()


def test_races_are_chronological_not_insertion_order(db):
    # Mirrors the real DB: Barcelona (round 7) was inserted before Monaco (round 6).
    add_race(db, 1, "Barcelona GP", "2026-06-14", 7)
    add_race(db, 2, "Monaco GP", "2026-06-07", 6)
    add_race(db, 3, "Early 2027 GP", "2027-03-01", 1)

    races = api.get_races(db)

    assert [r["name"] for r in races] == ["Monaco GP", "Barcelona GP", "Early 2027 GP"]
    assert races[-1]["name"] == "Early 2027 GP"


@pytest.mark.parametrize("endpoint", [api.get_results, api.get_laps, api.get_pitstops])
def test_unknown_race_id_returns_404(db, endpoint):
    with pytest.raises(HTTPException) as exc:
        endpoint(999, db)
    assert exc.value.status_code == 404


def test_results_laps_and_pits_have_deterministic_order(db):
    add_race(db, 1, "GP", "2026-03-01", 1)
    for pos in (3, 1, 2):
        db.add(DriverResult(race_id=1, position=pos, full_name=f"D{pos}"))
    db.add_all([
        LapPosition(race_id=1, driver="BBB", lap_number=2, position=1),
        LapPosition(race_id=1, driver="AAA", lap_number=1, position=2),
        LapPosition(race_id=1, driver="CCC", lap_number=1, position=1),
    ])
    db.add_all([
        PitStop(race_id=1, driver="BBB", lap_number=20, old_compound="SOFT", new_compound="HARD"),
        PitStop(race_id=1, driver="AAA", lap_number=10, old_compound="MEDIUM", new_compound="HARD"),
    ])
    db.commit()

    assert [r["position"] for r in api.get_results(1, db)] == [1, 2, 3]
    assert [(l["lap_number"], l["driver"]) for l in api.get_laps(1, db)] == [(1, "CCC"), (1, "AAA"), (2, "BBB")]
    assert [p["driver"] for p in api.get_pitstops(1, db)] == ["AAA", "BBB"]


def test_championship_defaults_to_latest_season_and_does_not_mix_years(db):
    add_race(db, 1, "GP", "2026-03-01", 1)
    add_race(db, 2, "GP", "2027-03-01", 1)  # same name and round, different season
    db.add(DriverResult(race_id=1, position=1, full_name="Old Champ", team="A"))
    db.add(DriverResult(race_id=2, position=1, full_name="New Champ", team="B"))
    db.commit()

    assert api.get_championship(None, None, db) == [{"full_name": "New Champ", "team": "B", "points": 25}]
    assert api.get_championship(2026, None, db) == [{"full_name": "Old Champ", "team": "A", "points": 25}]
    assert api.get_championship(2025, None, db) == []


def test_championship_points_include_sprint_and_no_fastest_lap_point(db):
    add_race(db, 1, "Sprint GP", "2026-03-01", 1)
    db.add_all([
        DriverResult(race_id=1, position=1, full_name="Winner", team="A"),
        DriverResult(race_id=1, position=11, full_name="Outside", team="B"),
        SprintResult(race_id=1, position=1, full_name="Winner", team="A"),
        SprintResult(race_id=1, position=9, full_name="Outside", team="B"),
    ])
    db.commit()
    # fastest lap recorded on the race must not add a point in 2026
    db.query(Race).update({"fastest_lap_driver": "OUT"})
    db.commit()

    table = {e["full_name"]: e["points"] for e in api.get_championship(None, None, db)}

    assert table == {"Winner": 25 + 8, "Outside": 0}


def test_championship_uses_most_recent_team_and_breaks_ties_by_name(db):
    add_race(db, 1, "GP1", "2026-03-01", 1)
    add_race(db, 2, "GP2", "2026-03-08", 2)
    db.add_all([
        DriverResult(race_id=2, position=2, full_name="Switcher", team="New Team"),
        DriverResult(race_id=1, position=1, full_name="Switcher", team="Old Team"),
        DriverResult(race_id=1, position=2, full_name="Alpha", team="X"),
        DriverResult(race_id=2, position=1, full_name="Zulu", team="Y"),
    ])
    db.commit()

    table = api.get_championship(None, None, db)

    switcher = next(e for e in table if e["full_name"] == "Switcher")
    assert switcher["team"] == "New Team"
    # Switcher 25+18=43, Zulu 25, Alpha 18
    assert [e["full_name"] for e in table] == ["Switcher", "Zulu", "Alpha"]


def seed_two_seasons(db):
    add_race(db, 1, "S26 R1", "2026-03-01", 1)
    add_race(db, 2, "S26 R2", "2026-03-08", 2)
    add_race(db, 3, "S27 R1", "2027-03-01", 1)
    db.add_all([
        DriverResult(race_id=1, position=1, full_name="Ann", team="A"),
        DriverResult(race_id=2, position=1, full_name="Bob", team="B"),
        SprintResult(race_id=2, position=1, full_name="Bob", team="B"),
        DriverResult(race_id=3, position=1, full_name="Cy", team="C"),
        SprintResult(race_id=3, position=2, full_name="Cy", team="C"),
        SprintResult(race_id=3, position=1, full_name="Dee", team="D"),
    ])
    db.commit()


def test_season_filter_applies_to_race_and_sprint_results_alike(db):
    seed_two_seasons(db)

    t26 = {e["full_name"]: e["points"] for e in api.get_championship(2026, None, db)}
    t27 = {e["full_name"]: e["points"] for e in api.get_championship(2027, None, db)}

    assert t26 == {"Ann": 25, "Bob": 25 + 8}
    assert t27 == {"Cy": 25 + 7, "Dee": 8}  # no 2026 race or sprint points leak in


def test_through_round_gives_standings_after_that_round(db):
    seed_two_seasons(db)

    after_r1 = api.get_championship(2026, 1, db)
    after_r2 = api.get_championship(2026, 2, db)

    assert after_r1 == [{"full_name": "Ann", "team": "A", "points": 25}]
    assert {e["full_name"] for e in after_r2} == {"Ann", "Bob"}
    assert api.get_championship(2026, 0, db) == []


def test_through_round_does_not_match_same_round_in_other_season(db):
    seed_two_seasons(db)

    names = {e["full_name"] for e in api.get_championship(2027, 1, db)}

    assert names == {"Cy", "Dee"}


def test_championship_edge_cases(db):
    assert api.get_championship(None, None, db) == []  # empty DB
    add_race(db, 1, "No Date", None, 1)
    db.add(DriverResult(race_id=1, position=1, full_name="Ghost", team="G"))
    db.commit()
    assert api.get_championship(None, None, db) == []  # undated races never count
    assert api.get_championship(2026, None, db) == []


def test_sprint_only_driver_and_season_with_only_sprint_rows(db):
    add_race(db, 1, "GP", "2026-03-01", 1)
    db.add(SprintResult(race_id=1, position=3, full_name="Sprinter", team="S"))
    db.commit()

    assert api.get_championship(2026, None, db) == [{"full_name": "Sprinter", "team": "S", "points": 6}]


# --- circuit map endpoint -------------------------------------------------

from models import CircuitMap


def test_circuit_endpoint_returns_available_map(db):
    add_race(db, 1, "GP", "2026-03-01", 1)
    db.add(CircuitMap(race_id=1, status="available", source="multiviewer", data='{"outline":[[0,0]],"corners":[]}'))
    db.commit()

    body = api.get_circuit_map(1, db)

    assert body["status"] == "available" and body["map"] == {"outline": [[0, 0]], "corners": []}


def test_circuit_endpoint_reports_unavailable_with_reason(db):
    add_race(db, 1, "Madrid GP", "2026-09-13", 14)
    add_race(db, 2, "Unfetched GP", "2026-09-20", 15)
    db.add(CircuitMap(race_id=1, status="unavailable", reason="no_data"))
    db.commit()

    assert api.get_circuit_map(1, db) == {"status": "unavailable", "reason": "no_data", "map": None}
    assert api.get_circuit_map(2, db) == {"status": "unavailable", "reason": "not_fetched", "map": None}


def test_circuit_endpoint_survives_corrupt_stored_json_and_unknown_race(db):
    add_race(db, 1, "GP", "2026-03-01", 1)
    db.add(CircuitMap(race_id=1, status="available", data="{not json"))
    db.commit()

    assert api.get_circuit_map(1, db)["reason"] == "corrupt_data"
    with pytest.raises(HTTPException) as exc:
        api.get_circuit_map(999, db)
    assert exc.value.status_code == 404
