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

    assert lines.index("ANT left the pits on lap 15 on HARD tyres") < lines.index("VER left the pits on lap 30 on HARD tyres")


def test_generate_summary_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = summarizer.generate_summary(
        race_info={"name": "Test GP", "date": "2026-01-01", "total_laps": 10},
        results=[{"Position": "1", "FullName": "A Driver", "TeamName": "A Team", "Time": "1:00:00"}],
        pit_stops=[],
    )

    assert result is None


from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Race, DriverResult, PitStop

RACE_INFO = {
    "name": "Test GP", "date": "2026-01-01", "total_laps": 10, "location": "Testville",
    "air_temp": 21.5, "track_temp": 33.0, "rainfall": "No",
    "fastest_lap_driver": "ADR", "fastest_lap_time": "0 days 00:01:22.091000", "fastest_lap_number": 7,
}
RESULTS = [
    {"Position": 1, "FullName": "A Driver", "TeamName": "A Team", "Time": "0 days 01:23:06.801000", "GridPosition": 3},
    {"Position": 2, "FullName": "B Driver", "TeamName": "B Team", "Time": "NaT", "GridPosition": 0},
]
PITS = [{"Driver": "ADR", "LapNumber": 5, "NewCompound": "HARD"}]


def fake_anthropic(monkeypatch, reply=None, error=None):
    captured = {}

    class FakeClient:
        def __init__(self):
            self.messages = self

        def create(self, **kwargs):
            captured.update(kwargs)
            if error:
                raise error
            return SimpleNamespace(content=reply)

    monkeypatch.setattr(summarizer.anthropic, "Anthropic", FakeClient)
    return captured


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def test_prompt_contains_grounding_rules_and_only_supplied_facts():
    prompt = summarizer.build_prompt(RACE_INFO, RESULTS, PITS)

    assert "Do not invent" in prompt
    assert "driver quotes" in prompt
    assert "P1: A Driver (A Team) - 1:23:06.801 [started P3]" in prompt
    assert "P2: B Driver (B Team) - no time recorded" in prompt  # grid 0 not shown as a slot
    assert "[started P0]" not in prompt
    assert "Fastest lap: ADR 1:22.091 on lap 7" in prompt
    assert "air temperature 21.5C" in prompt
    assert "ADR left the pits on lap 5 on HARD tyres" in prompt
    assert "days" not in prompt.split("Do not invent")[1].split("Style:")[1]  # raw timedeltas never leak


def test_prompt_omits_facts_that_are_unavailable():
    info = {"name": "Test GP", "date": "2026-01-01", "total_laps": 10}

    prompt = summarizer.build_prompt(info, RESULTS, [])

    assert "Fastest lap" not in prompt
    assert "temperature" not in prompt
    assert "Location" not in prompt


def test_generate_summary_returns_fake_model_text_and_sends_prompt(monkeypatch):
    captured = fake_anthropic(monkeypatch, reply=[text_block("  Title\n\nBody  ")])

    assert summarizer.generate_summary(RACE_INFO, RESULTS, PITS) == "Title\n\nBody"
    assert "Do not invent" in captured["messages"][0]["content"]


def test_generate_summary_handles_api_errors_empty_and_non_text_replies(monkeypatch):
    fake_anthropic(monkeypatch, error=RuntimeError("rate limited"))
    assert summarizer.generate_summary(RACE_INFO, RESULTS, PITS) is None

    fake_anthropic(monkeypatch, reply=[text_block("   ")])
    assert summarizer.generate_summary(RACE_INFO, RESULTS, PITS) is None

    fake_anthropic(monkeypatch, reply=[SimpleNamespace(type="tool_use")])
    assert summarizer.generate_summary(RACE_INFO, RESULTS, PITS) is None


def test_generate_summary_skips_model_call_when_there_are_no_results(monkeypatch):
    captured = fake_anthropic(monkeypatch, reply=[text_block("should not be used")])

    assert summarizer.generate_summary(RACE_INFO, [], PITS) is None
    assert captured == {}


def test_backfill_saves_summary_and_leaves_failures_for_retry(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add_all([
        Race(race_id=1, name="Good GP", date="2026-01-01", round=1, total_laps=10, rainfall="No"),
        Race(race_id=2, name="Failing GP", date="2026-01-08", round=2, total_laps=10),
        DriverResult(race_id=1, position=1, full_name="A", team="T", time="NaT", grid_position=1),
        DriverResult(race_id=2, position=1, full_name="B", team="T", time="NaT", grid_position=1),
        PitStop(race_id=1, driver="A", lap_number=3, old_compound="SOFT", new_compound="HARD"),
    ])
    db.commit()
    db.close()
    monkeypatch.setattr(summarizer, "SessionLocal", Session)
    monkeypatch.setattr(
        summarizer, "generate_summary",
        lambda info, results, pits: "A summary" if info["name"] == "Good GP" else None,
    )

    summarizer.backfill_summaries()

    check = Session()
    assert check.get(Race, 1).summary == "A summary"
    assert check.get(Race, 2).summary is None  # picked up again on the next run


# --- stale summary detection and selective regeneration -------------------

import regenerate_summaries
from models import RaceMeta


def seeded_session(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add_all([
        Race(race_id=1, name="Legacy GP", date="2026-01-01", round=1, summary="old text"),
        Race(race_id=2, name="Current GP", date="2026-01-08", round=2, summary="new text"),
        Race(race_id=3, name="Legacy GP 2", date="2026-01-15", round=3, summary="older text"),
        Race(race_id=4, name="Unsummarised GP", date="2026-01-22", round=4, summary=None),
        RaceMeta(race_id=2, summary_prompt_version=summarizer.PROMPT_VERSION),
    ])
    for rid in (1, 2, 3, 4):
        db.add(DriverResult(race_id=rid, position=1, full_name="A", team="T", time="NaT", grid_position=1))
    db.commit()
    db.close()
    monkeypatch.setattr(summarizer, "SessionLocal", Session)
    monkeypatch.setattr(regenerate_summaries, "SessionLocal", Session)
    return Session


def test_find_stale_summaries_flags_only_old_prompt_summaries(monkeypatch):
    Session = seeded_session(monkeypatch)

    stale = summarizer.find_stale_summaries(Session())

    # race 2 is current; race 4 has no summary at all (backfill handles it, not regeneration)
    assert [(r.race_id, v) for r, v in stale] == [(1, 1), (3, 1)]


def test_dry_run_lists_without_model_calls_or_writes(monkeypatch, capsys):
    Session = seeded_session(monkeypatch)
    calls = []
    monkeypatch.setattr(summarizer, "generate_summary", lambda *a: calls.append(a) or "X")

    assert regenerate_summaries.main([]) == 0

    out = capsys.readouterr().out
    assert "Stale summaries: 2" in out and "Legacy GP" in out and "Dry run" in out
    assert calls == []
    assert Session().get(Race, 1).summary == "old text"


def test_apply_regenerates_only_selected_ids_and_marks_them_current(monkeypatch):
    Session = seeded_session(monkeypatch)
    monkeypatch.setattr(summarizer, "generate_summary", lambda *a: "fresh text")

    assert regenerate_summaries.main(["--apply", "--ids", "1"]) == 0

    db = Session()
    assert db.get(Race, 1).summary == "fresh text"
    assert db.get(RaceMeta, 1).summary_prompt_version == summarizer.PROMPT_VERSION
    assert db.get(Race, 3).summary == "older text"  # not selected, untouched
    assert [r.race_id for r, _ in summarizer.find_stale_summaries(db)] == [3]


def test_failed_regeneration_keeps_old_summary_and_stays_retryable(monkeypatch):
    Session = seeded_session(monkeypatch)
    monkeypatch.setattr(summarizer, "generate_summary", lambda *a: None)

    assert regenerate_summaries.main(["--apply"]) == 1  # non-zero: something failed

    db = Session()
    assert db.get(Race, 1).summary == "old text"
    assert db.get(Race, 3).summary == "older text"
    assert [r.race_id for r, _ in summarizer.find_stale_summaries(db)] == [1, 3]

    monkeypatch.setattr(summarizer, "generate_summary", lambda *a: "recovered")
    assert regenerate_summaries.main(["--apply"]) == 0
    assert summarizer.find_stale_summaries(Session()) == []


def test_limit_caps_the_number_of_regenerations(monkeypatch):
    Session = seeded_session(monkeypatch)
    monkeypatch.setattr(summarizer, "generate_summary", lambda *a: "fresh")

    regenerated, failed = summarizer.regenerate_stale_summaries(limit=1)

    assert regenerated == ["Legacy GP"] and failed == []
    assert [r.race_id for r, _ in summarizer.find_stale_summaries(Session())] == [3]


def test_backfill_records_prompt_version_and_failed_generation_stays_null(monkeypatch):
    Session = seeded_session(monkeypatch)
    monkeypatch.setattr(summarizer, "generate_summary", lambda *a: None)
    summarizer.backfill_summaries()
    assert Session().get(Race, 4).summary is None  # retried next run

    monkeypatch.setattr(summarizer, "generate_summary", lambda *a: "ok")
    summarizer.backfill_summaries()
    db = Session()
    assert db.get(Race, 4).summary == "ok"
    assert db.get(RaceMeta, 4).summary_prompt_version == summarizer.PROMPT_VERSION
