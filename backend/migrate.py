"""Explicit, versioned, additive migrations for SQLite and PostgreSQL.

Run once before deploying new code: python migrate.py
Existing data is preserved. Duplicate identities stop migration for manual review.
"""
from sqlalchemy import inspect, text
from database import engine
from models import Base

SCHEMA_VERSION = 1


def check_schema(target=engine):
    try:
        with target.connect() as conn:
            version = conn.execute(text("SELECT MAX(version) FROM schema_migrations")).scalar()
    except Exception as exc:
        raise RuntimeError("Database is not migrated. Run python migrate.py first.") from exc
    if version != SCHEMA_VERSION:
        raise RuntimeError("Database schema does not match this application. Run python migrate.py.")


def upgrade(target=engine):
    with target.connect() as conn:
        # Serialize migration processes independently of the workflow scheduler.
        if target.dialect.name == "sqlite":
            conn.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            conn.begin()
            conn.execute(text("SELECT pg_advisory_xact_lock(48173001)"))
        try:
            conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"))
            version = conn.execute(text("SELECT MAX(version) FROM schema_migrations")).scalar() or 0
            if version > SCHEMA_VERSION:
                raise RuntimeError("Database is newer than this application")
            if version < 1:
                tables = set(inspect(conn).get_table_names())
                identities = {
                    "races": "substr(date, 1, 4), round",
                    "results": "race_id, full_name",
                    "sprint_results": "race_id, full_name",
                    "lap_positions": "race_id, driver, lap_number",
                }
                for table, columns in identities.items():
                    if table in tables:
                        duplicate = conn.execute(text(
                            f"SELECT 1 FROM {table} GROUP BY {columns} HAVING COUNT(*) > 1 LIMIT 1"
                        )).first()
                        if duplicate:
                            raise RuntimeError(f"Duplicate identities in {table}; review these rows before migrating")
                Base.metadata.create_all(conn)
                for table in ("results", "sprint_results"):
                    columns = {c["name"] for c in inspect(conn).get_columns(table)}
                    for name, kind in (("points", "FLOAT"), ("status", "VARCHAR")):
                        if name not in columns:
                            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {kind}"))
                # create_all does not add indexes/constraints to existing tables.
                for table in Base.metadata.sorted_tables:
                    for index in table.indexes:
                        if index.name != "uq_races_season_round":
                            index.create(conn, checkfirst=True)
                for table, columns in identities.items():
                    name = {"races": "uq_races_season_round", "results": "uq_results_race_driver",
                            "sprint_results": "uq_sprint_results_race_driver",
                            "lap_positions": "uq_lap_positions_race_driver_lap"}[table]
                    conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table} ({columns})"))
                conn.execute(text("INSERT INTO schema_migrations (version) VALUES (1)"))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


if __name__ == "__main__":
    upgrade()
    print(f"Database schema is at version {SCHEMA_VERSION}")
