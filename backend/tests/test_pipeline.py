from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pipeline
from models import Base, Race


def make_test_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_run_pending_races_only_fetches_missing_rounds(monkeypatch):
    TestSessionLocal = make_test_session_factory()

    db = TestSessionLocal()
    db.add(Race(name="Already Fetched GP", round=1))
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

    fetched = []
    monkeypatch.setattr(
        pipeline,
        "run_pipeline",
        lambda year, race, has_sprint=False: fetched.append((race, has_sprint)),
    )

    pipeline.run_pending_races(2026)

    assert fetched == [("New GP", True)]
