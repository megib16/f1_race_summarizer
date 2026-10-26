import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import pipeline
from models import Base, Race, DriverResult, LapPosition, PitStop, SprintResult, RaceMeta


def make_test_session_factory():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_run_pending_races_only_fetches_missing_rounds(monkeypatch):
    TestSessionLocal = make_test_session_factory()

    db = TestSessionLocal()
    db.add(Race(name="Already Fetched GP", round=1, date="2026-03-01"))
    db.commit()
    db.close()

    monkeypatch.setattr(pipeline, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(
        pipeline.fetcher,
        "get_completed_races",
        lambda year: [
            {"round": 1, "name": "Already Fetched GP", "has_sprint": False},
            {"round": 2, "name": "New GP", "has_sprint": True},
        ],
    )
    monkeypatch.setattr(pipeline.summarizer, "backfill_summaries", lambda: None)
    monkeypatch.setattr(pipeline, "backfill_circuit_maps", lambda **kw: [])

    fetched = []
    monkeypatch.setattr(
        pipeline,
        "run_pipeline",
        lambda year, race, has_sprint=False: fetched.append((race, has_sprint)) or True,
    )

    failed = pipeline.run_pending_races(2026)

    # fetched by round number (FastF1 name matching is fuzzy), not by name
    assert fetched == [(2, True)]
    assert failed == []


def test_run_pending_races_does_not_skip_a_round_already_stored_for_another_season(monkeypatch):
    TestSessionLocal = make_test_session_factory()
    db = TestSessionLocal()
    db.add(Race(name="Old GP", round=1, date="2026-03-01"))
    db.commit()
    db.close()

    monkeypatch.setattr(pipeline, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(
        pipeline.fetcher, "get_completed_races",
        lambda year: [{"round": 1, "name": "New Season GP", "has_sprint": False}],
    )
    monkeypatch.setattr(pipeline.summarizer, "backfill_summaries", lambda: None)
    monkeypatch.setattr(pipeline, "backfill_circuit_maps", lambda **kw: [])
    fetched = []
    monkeypatch.setattr(pipeline, "run_pipeline", lambda year, race, has_sprint=False: fetched.append(race) or True)

    pipeline.run_pending_races(2027)

    assert fetched == [1]


def test_run_pending_races_reports_failures(monkeypatch):
    monkeypatch.setattr(pipeline, "SessionLocal", make_test_session_factory())
    monkeypatch.setattr(
        pipeline.fetcher, "get_completed_races",
        lambda year: [{"round": 1, "name": "Broken GP", "has_sprint": False}],
    )
    monkeypatch.setattr(pipeline.summarizer, "backfill_summaries", lambda: None)
    monkeypatch.setattr(pipeline, "backfill_circuit_maps", lambda **kw: [])
    monkeypatch.setattr(pipeline, "run_pipeline", lambda *a, **k: False)

    assert pipeline.run_pending_races(2026) == ["Broken GP"]


class FakeSession:
    pass


def install_fake_fetcher(monkeypatch, *, name="Test GP", date="2026-03-01", rnd=1,
                         results=None, fastest_lap="default", sprint="none"):
    """Replace every fetcher call used by run_pipeline so no FastF1/network is touched."""
    f = pipeline.fetcher
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
        {"Position": float("nan"), "FullName": "B Driver", "TeamName": "Team B"},
    ])


@pytest.fixture
def pipeline_db(monkeypatch):
    TestSessionLocal = make_test_session_factory()
    monkeypatch.setattr(pipeline, "SessionLocal", TestSessionLocal)
    return TestSessionLocal


def test_run_pipeline_stores_race_when_fastest_lap_is_missing(monkeypatch, pipeline_db):
    install_fake_fetcher(monkeypatch, fastest_lap=None)

    assert pipeline.run_pipeline(2026, 1) is True

    db = pipeline_db()
    race = db.query(Race).one()
    assert race.fastest_lap_driver is None
    assert db.query(DriverResult).count() == 2


def test_run_pipeline_tolerates_nan_grid_and_skips_nan_positions(monkeypatch, pipeline_db):
    results = [
        {"Position": 1.0, "GridPosition": float("nan"), "FullName": "A", "TeamName": "T", "Abbreviation": "A", "Time": "t"},
        {"Position": float("nan"), "GridPosition": 3.0, "FullName": "B", "TeamName": "T", "Abbreviation": "B", "Time": "t"},
    ]
    install_fake_fetcher(monkeypatch, results=results)

    assert pipeline.run_pipeline(2026, 1) is True

    db = pipeline_db()
    rows = db.query(DriverResult).all()
    assert [(r.full_name, r.position, r.grid_position) for r in rows] == [("A", 1, None)]
    assert db.query(LapPosition).count() == 1  # NaN-position lap skipped


def test_run_pipeline_returns_false_when_session_cannot_load(monkeypatch, pipeline_db):
    monkeypatch.setattr(pipeline.fetcher, "load_session", lambda y, r: None)

    assert pipeline.run_pipeline(2026, 1) is False
    assert pipeline_db().query(Race).count() == 0


def test_run_pipeline_is_idempotent_keeps_race_id_and_sprint(monkeypatch, pipeline_db):
    install_fake_fetcher(monkeypatch)
    assert pipeline.run_pipeline(2026, 1, has_sprint=True)
    first_id = pipeline_db().query(Race).one().race_id

    assert pipeline.run_pipeline(2026, 1, has_sprint=True)

    db = pipeline_db()
    assert db.query(Race).one().race_id == first_id
    assert db.query(DriverResult).count() == 2
    assert db.query(PitStop).count() == 1
    assert db.query(LapPosition).count() == 1
    assert db.query(SprintResult).count() == 1  # NaN sprint position skipped, not duplicated


def test_race_is_stored_when_sprint_is_unavailable(monkeypatch, pipeline_db):
    install_fake_fetcher(monkeypatch, sprint="unavailable")

    assert pipeline.run_pipeline(2026, 1, has_sprint=True) is True

    db = pipeline_db()
    assert db.query(Race).count() == 1
    assert db.query(DriverResult).count() == 2
    assert db.query(SprintResult).count() == 0


def test_race_is_stored_when_sprint_loading_raises(monkeypatch, pipeline_db):
    install_fake_fetcher(monkeypatch)
    def boom(y, r):
        raise RuntimeError("network down")
    monkeypatch.setattr(pipeline.fetcher, "load_sprint_session", boom)

    assert pipeline.run_pipeline(2026, 1, has_sprint=True) is True
    assert pipeline_db().query(Race).count() == 1


def test_rerun_with_sprint_unavailable_keeps_existing_sprint_rows(monkeypatch, pipeline_db):
    install_fake_fetcher(monkeypatch)
    assert pipeline.run_pipeline(2026, 1, has_sprint=True)
    install_fake_fetcher(monkeypatch, sprint="unavailable")

    assert pipeline.run_pipeline(2026, 1, has_sprint=True)
    assert pipeline.run_pipeline(2026, 1)  # has_sprint defaults to False

    assert pipeline_db().query(SprintResult).count() == 1


import datetime

TODAY = datetime.date(2026, 5, 1)


def ingest_without_sprint(monkeypatch, pipeline_db):
    """Ingest round 1 on TODAY with the sprint unavailable (counts as attempt 1)."""
    install_fake_fetcher(monkeypatch, sprint="unavailable")
    monkeypatch.setattr(pipeline.datetime, "date", type("D", (datetime.date,), {"today": classmethod(lambda cls: TODAY)}))
    assert pipeline.run_pipeline(2026, 1, has_sprint=True)
    return [{"round": 1, "name": "Test GP", "has_sprint": True}]


def count_sprint_loads(monkeypatch, available):
    calls = []
    def load(y, r):
        calls.append(r)
        return FakeSession() if available() else None
    monkeypatch.setattr(pipeline.fetcher, "load_sprint_session", load)
    return calls


def test_sprint_added_on_later_run_via_backfill(monkeypatch, pipeline_db):
    events = ingest_without_sprint(monkeypatch, pipeline_db)
    state = {"up": False}
    install_fake_fetcher(monkeypatch)
    calls = count_sprint_loads(monkeypatch, lambda: state["up"])
    later = TODAY + datetime.timedelta(days=3)

    # Due but still unavailable: reported as pending, nothing written, no exception.
    assert pipeline.backfill_sprints(2026, events, today=later) == ["Test GP"]
    assert pipeline_db().query(SprintResult).count() == 0

    state["up"] = True  # sprint now available
    much_later = later + datetime.timedelta(days=7)
    assert pipeline.backfill_sprints(2026, events, today=much_later) == []
    assert pipeline_db().query(SprintResult).count() == 1

    # Idempotent and no further loads once rows exist.
    n = len(calls)
    assert pipeline.backfill_sprints(2026, events, today=much_later) == []
    assert pipeline_db().query(SprintResult).count() == 1
    assert len(calls) == n


def test_unavailable_sprint_is_not_reloaded_every_day(monkeypatch, pipeline_db):
    events = ingest_without_sprint(monkeypatch, pipeline_db)  # attempt 1 on TODAY
    install_fake_fetcher(monkeypatch)
    calls = count_sprint_loads(monkeypatch, lambda: False)

    # Daily runs for 30 days against a permanently unavailable sprint.
    for day in range(1, 31):
        pipeline.backfill_sprints(2026, events, today=TODAY + datetime.timedelta(days=day))

    # Backoff: 2d, 4d, then weekly -> far fewer than 30 loads, but never zero.
    assert 3 <= len(calls) <= 6
    meta = pipeline_db().query(RaceMeta).one()
    assert meta.sprint_attempts == 1 + len(calls)


def test_sprint_retry_delay_schedule():
    assert [pipeline.sprint_retry_delay_days(n) for n in (0, 1, 2, 3, 4, 10)] == [0, 2, 4, 7, 7, 7]


def test_sprint_attempt_metadata_is_reset_when_race_is_reingested(monkeypatch, pipeline_db):
    ingest_without_sprint(monkeypatch, pipeline_db)
    assert pipeline_db().query(RaceMeta).count() == 1

    install_fake_fetcher(monkeypatch)  # sprint available on the re-run
    assert pipeline.run_pipeline(2026, 1, has_sprint=True)

    db = pipeline_db()
    assert db.query(SprintResult).count() == 1
    assert db.query(RaceMeta).count() == 0


def test_run_pending_races_retries_missing_sprint_without_failing(monkeypatch, pipeline_db, capsys):
    events = ingest_without_sprint(monkeypatch, pipeline_db)
    monkeypatch.setattr(pipeline.fetcher, "get_completed_races", lambda year: events)
    monkeypatch.setattr(pipeline.summarizer, "backfill_summaries", lambda: None)
    monkeypatch.setattr(pipeline, "backfill_circuit_maps", lambda **kw: [])
    install_fake_fetcher(monkeypatch)
    state = {"up": False}
    count_sprint_loads(monkeypatch, lambda: state["up"])
    later = TODAY + datetime.timedelta(days=3)

    assert pipeline.run_pending_races(2026, today=later) == []  # not a failure
    assert "Sprint results still unavailable for: Test GP" in capsys.readouterr().out

    state["up"] = True
    assert pipeline.run_pending_races(2026, today=later + datetime.timedelta(days=7)) == []
    assert pipeline_db().query(SprintResult).count() == 1


def test_backfill_ignores_non_sprint_events_and_unstored_races(monkeypatch, pipeline_db):
    install_fake_fetcher(monkeypatch)
    events = [
        {"round": 1, "name": "No Sprint", "has_sprint": False},
        {"round": 9, "name": "Not Stored Yet", "has_sprint": True},
    ]
    assert pipeline.backfill_sprints(2026, events) == []


def test_same_name_in_a_different_season_is_a_separate_race(monkeypatch, pipeline_db):
    install_fake_fetcher(monkeypatch, name="Test GP", date="2026-03-01", rnd=1)
    assert pipeline.run_pipeline(2026, 1)
    install_fake_fetcher(monkeypatch, name="Test GP", date="2027-03-01", rnd=1)
    assert pipeline.run_pipeline(2027, 1)

    dates = sorted(r.date for r in pipeline_db().query(Race).all())
    assert dates == ["2026-03-01", "2027-03-01"]


# --- circuit maps ---------------------------------------------------------

import json
from models import CircuitMap
from tests.test_circuit import raw_payload


def stub_circuit_source(monkeypatch, payload=..., key=15, error=None):
    calls = []

    def fetch(year, circuit_key):
        calls.append((year, circuit_key))
        if error:
            raise error
        return raw_payload() if payload is ... else payload

    monkeypatch.setattr(pipeline.fetcher, "get_circuit_key", lambda s: key)
    monkeypatch.setattr(pipeline.fetcher, "fetch_circuit_payload", fetch)
    return calls


def test_ingest_stores_circuit_map_for_the_races_own_year(monkeypatch, pipeline_db):
    install_fake_fetcher(monkeypatch)
    calls = stub_circuit_source(monkeypatch)

    assert pipeline.run_pipeline(2026, 1)

    row = pipeline_db().query(CircuitMap).one()
    assert calls == [(2026, 15)]  # layouts change by year: always ask for this race's season
    assert row.status == "available" and row.circuit_key == 15
    assert json.loads(row.data)["circuit_name"] == "Test Circuit"


def test_source_without_data_is_recorded_as_unavailable(monkeypatch, pipeline_db):
    install_fake_fetcher(monkeypatch)
    stub_circuit_source(monkeypatch, payload=None, key=153)

    assert pipeline.run_pipeline(2026, 1)

    row = pipeline_db().query(CircuitMap).one()
    assert (row.status, row.reason, row.data) == ("unavailable", "no_data", None)


def test_circuit_lookup_error_never_blocks_the_race_and_is_not_recorded(monkeypatch, pipeline_db):
    install_fake_fetcher(monkeypatch)
    stub_circuit_source(monkeypatch, error=ConnectionError("offline"))

    assert pipeline.run_pipeline(2026, 1) is True

    db = pipeline_db()
    assert db.query(Race).count() == 1
    assert db.query(CircuitMap).count() == 0  # retried next run


def test_reingest_keeps_previous_map_if_lookup_fails_then_replaces_it(monkeypatch, pipeline_db):
    install_fake_fetcher(monkeypatch)
    stub_circuit_source(monkeypatch)
    assert pipeline.run_pipeline(2026, 1)
    before = pipeline_db().query(CircuitMap).one().data

    stub_circuit_source(monkeypatch, error=ConnectionError("offline"))
    assert pipeline.run_pipeline(2026, 1)
    assert pipeline_db().query(CircuitMap).one().data == before

    stub_circuit_source(monkeypatch, payload=raw_payload(rotation=90))
    assert pipeline.run_pipeline(2026, 1)
    rows = pipeline_db().query(CircuitMap).all()
    assert len(rows) == 1 and json.loads(rows[0].data)["rotation"] == 90


def seed_races(pipeline_db):
    db = pipeline_db()
    db.add_all([
        Race(race_id=1, name="Barcelona GP", date="2026-06-14", round=7),
        Race(race_id=2, name="Madrid GP", date="2026-09-13", round=14),
        Race(race_id=3, name="Undated", date=None, round=None),
    ])
    db.commit()


def stub_backfill_sources(monkeypatch, keys, payloads, errors=()):
    asked = []
    monkeypatch.setattr(pipeline.fetcher, "load_session_info", lambda year, rnd: (year, rnd))
    monkeypatch.setattr(pipeline.fetcher, "get_circuit_key", lambda s: keys[s])

    def fetch(year, key):
        asked.append((year, key))
        if key in errors:
            raise ConnectionError("offline")
        return payloads.get(key)

    monkeypatch.setattr(pipeline.fetcher, "fetch_circuit_payload", fetch)
    return asked


def test_backfill_fills_missing_maps_and_reports_races_without_one(monkeypatch, pipeline_db):
    seed_races(pipeline_db)
    stub_backfill_sources(monkeypatch, {(2026, 7): 15, (2026, 14): 153}, {15: raw_payload()})

    missing = pipeline.backfill_circuit_maps()

    rows = {r.race_id: r.status for r in pipeline_db().query(CircuitMap)}
    assert rows == {1: "available", 2: "unavailable"}  # undated race skipped
    assert missing == ["Madrid GP"]


def test_backfill_does_not_refetch_existing_or_unavailable_unless_asked(monkeypatch, pipeline_db):
    seed_races(pipeline_db)
    keys = {(2026, 7): 15, (2026, 14): 153}
    asked = stub_backfill_sources(monkeypatch, keys, {15: raw_payload()})
    pipeline.backfill_circuit_maps()
    asked.clear()

    pipeline.backfill_circuit_maps()
    assert asked == []  # nothing re-requested on a normal run

    stub_backfill_sources(monkeypatch, keys, {15: raw_payload(), 153: raw_payload()})
    assert pipeline.backfill_circuit_maps(retry_unavailable=True) == []
    statuses = {r.race_id: r.status for r in pipeline_db().query(CircuitMap)}
    assert statuses == {1: "available", 2: "available"}


def test_backfill_network_error_records_nothing_so_it_is_retried(monkeypatch, pipeline_db):
    seed_races(pipeline_db)
    stub_backfill_sources(monkeypatch, {(2026, 7): 15, (2026, 14): 153}, {}, errors=(15, 153))

    missing = pipeline.backfill_circuit_maps()

    assert sorted(missing) == ["Barcelona GP", "Madrid GP"]
    assert pipeline_db().query(CircuitMap).count() == 0
