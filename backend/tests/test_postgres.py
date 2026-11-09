"""Run against an isolated schema on CI's disposable PostgreSQL service."""
import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

import pipeline
from migrate import upgrade, check_schema
from models import Race, DriverResult, SprintResult
from tests.test_pipeline import install_fake_fetcher


@pytest.mark.skipif(not os.environ.get("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL is not configured")
def test_postgres_migration_ingestion_and_constraints(monkeypatch):
    url = os.environ["TEST_POSTGRES_URL"]
    schema = "test_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        upgrade(engine)
        upgrade(engine)
        check_schema(engine)
        Session = sessionmaker(bind=engine)
        monkeypatch.setattr(pipeline, "SessionLocal", Session)
        install_fake_fetcher(monkeypatch)
        assert pipeline.run_pipeline(2026, 1, has_sprint=True)
        assert pipeline.run_pipeline(2026, 1, has_sprint=True)
        with Session() as db:
            assert db.query(Race).count() == 1
            assert db.query(DriverResult).count() == 2
            assert db.query(SprintResult).count() == 2
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(text("INSERT INTO races (date, round) VALUES ('2026-03-02', 1)"))
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
