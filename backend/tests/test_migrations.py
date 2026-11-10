import os
import shutil

import pytest
from sqlalchemy import text, inspect
from sqlalchemy.exc import IntegrityError

from database import make_engine, database_url
from migrate import upgrade, check_schema


def test_migrates_existing_database_without_losing_data(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE races (race_id INTEGER PRIMARY KEY, name VARCHAR, date VARCHAR, round INTEGER)"))
        conn.execute(text("INSERT INTO races VALUES (1, 'GP', '2026-01-01', 1)"))
        conn.execute(text("CREATE TABLE results (driver_id INTEGER PRIMARY KEY, race_id INTEGER, full_name VARCHAR)"))
        conn.execute(text("INSERT INTO results VALUES (1, 1, 'A')"))
        conn.execute(text("CREATE TABLE sprint_results (id INTEGER PRIMARY KEY, race_id INTEGER, full_name VARCHAR)"))
    upgrade(engine)
    upgrade(engine)
    check_schema(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT full_name, points, status FROM results")).one() == ("A", None, None)
        assert conn.execute(text("SELECT name FROM races")).scalar() == "GP"
        assert "ix_results_race_id" in {i["name"] for i in inspect(conn).get_indexes("results")}
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(text("INSERT INTO races (race_id, date, round) VALUES (2, '2026-01-02', 1)"))
    engine.dispose()


def test_migration_refuses_duplicate_identities(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'duplicates.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE races (race_id INTEGER PRIMARY KEY, date VARCHAR, round INTEGER)"))
        conn.execute(text("INSERT INTO races VALUES (1, '2026-01-01', 1), (2, '2026-01-02', 1)"))
    with pytest.raises(RuntimeError, match="Duplicate identities"):
        upgrade(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM races")).scalar() == 2


def test_startup_requires_explicit_migration_and_production_url(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    with pytest.raises(RuntimeError, match="not migrated"):
        check_schema(engine)
    assert inspect(engine).get_table_names() == []
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database_url()


def test_real_database_copy_migrates(tmp_path):
    source = os.path.join(os.path.dirname(__file__), "..", "f1_races.db")
    if not os.path.isfile(source):
        pytest.skip("No local legacy database")
    copy = tmp_path / "races.db"
    shutil.copyfile(source, copy)
    engine = make_engine(f"sqlite:///{copy}")
    with engine.connect() as conn:
        before = conn.execute(text("SELECT count(*) FROM races")).scalar()
    upgrade(engine)
    check_schema(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM races")).scalar() == before


def test_historical_migration_does_not_read_current_models(tmp_path, monkeypatch):
    from sqlalchemy import Column, Integer, Table
    from models import Base
    future_table = Table("future_feature", Base.metadata, Column("id", Integer, primary_key=True))
    def forbidden(*args, **kwargs):
        raise AssertionError("A historical migration must not read live model metadata")
    monkeypatch.setattr(Base.metadata, "create_all", forbidden)
    engine = make_engine(f"sqlite:///{tmp_path / 'frozen.db'}")
    try:
        upgrade(engine)
        check_schema(engine)
        assert "future_feature" not in inspect(engine).get_table_names()
        assert "races" in inspect(engine).get_table_names()
    finally:
        Base.metadata.remove(future_table)
        engine.dispose()
