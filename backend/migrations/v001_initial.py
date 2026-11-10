"""Frozen schema for migration 1. Never import application models here."""
from sqlalchemy import inspect, text, Column, Integer, String, Float, ForeignKey, Text, Boolean, Index, func, MetaData, Table

metadata = MetaData()

races = Table('races', metadata,
    Column('race_id', Integer, primary_key=True),
    Column('name', String),
    Column('location', String),
    Column('date', String),
    Column('round', Integer),
    Column('total_laps', Integer),
    Column('summary', String),
    Column('fastest_lap_driver', String),
    Column('fastest_lap_time', String),
    Column('fastest_lap_number', Integer),
    Column('fastest_lap_team', String),
    Column('air_temp', Float),
    Column('track_temp', Float),
    Column('rainfall', String),
)

results = Table('results', metadata,
    Column('driver_id', Integer, primary_key=True),
    Column('race_id', Integer, ForeignKey('races.race_id'), index=True),
    Column('position', Integer),
    Column('grid_position', Integer),
    Column('full_name', String),
    Column('abbreviation', String),
    Column('team', String),
    Column('time', String),
    Column('fastest_lap', String),
    Column('points', Float),
    Column('status', String),
)
Index('uq_results_race_driver', results.c.race_id, results.c.full_name, unique=True)

lap_positions = Table('lap_positions', metadata,
    Column('id', Integer, primary_key=True),
    Column('race_id', Integer, ForeignKey('races.race_id'), index=True),
    Column('driver', String),
    Column('lap_number', Integer),
    Column('position', Integer),
)
Index('uq_lap_positions_race_driver_lap', lap_positions.c.race_id, lap_positions.c.driver, lap_positions.c.lap_number, unique=True)

pitstops = Table('pitstops', metadata,
    Column('id', Integer, primary_key=True),
    Column('race_id', Integer, ForeignKey('races.race_id'), index=True),
    Column('driver', String),
    Column('lap_number', Integer),
    Column('old_compound', String),
    Column('new_compound', String),
)

sprint_results = Table('sprint_results', metadata,
    Column('id', Integer, primary_key=True),
    Column('race_id', Integer, ForeignKey('races.race_id'), index=True),
    Column('position', Integer),
    Column('full_name', String),
    Column('team', String),
    Column('points', Float),
    Column('status', String),
)
Index('uq_sprint_results_race_driver', sprint_results.c.race_id, sprint_results.c.full_name, unique=True)

race_meta = Table('race_meta', metadata,
    Column('race_id', Integer, ForeignKey('races.race_id'), primary_key=True),
    Column('summary_prompt_version', Integer),
    Column('sprint_attempts', Integer, default=0),
    Column('sprint_last_attempt', String),
)

circuit_maps = Table('circuit_maps', metadata,
    Column('race_id', Integer, ForeignKey('races.race_id'), primary_key=True),
    Column('status', String, nullable=False),
    Column('reason', String),
    Column('circuit_key', Integer),
    Column('source', String),
    Column('data', Text),
    Column('fetched_at', String),
)

ingest_state = Table('ingest_state', metadata,
    Column('race_id', Integer, ForeignKey('races.race_id'), primary_key=True),
    Column('race_refreshed_at', String),
    Column('race_complete', Boolean, default=False),
    Column('sprint_refreshed_at', String),
    Column('sprint_complete', Boolean, default=False),
    Column('sprint_required', Boolean, default=False),
)

Index("uq_races_season_round", func.substr(races.c.date, 1, 4), races.c.round, unique=True)


def upgrade(conn):
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
    metadata.create_all(conn)
    for table in ("results", "sprint_results"):
        columns = {c["name"] for c in inspect(conn).get_columns(table)}
        for name, kind in (("points", "FLOAT"), ("status", "VARCHAR")):
            if name not in columns:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {kind}"))
    # create_all does not add indexes/constraints to existing tables.
    for table in metadata.sorted_tables:
        for index in table.indexes:
            if index.name != "uq_races_season_round":
                index.create(conn, checkfirst=True)
    for table, columns in identities.items():
        name = {"races": "uq_races_season_round", "results": "uq_results_race_driver",
                "sprint_results": "uq_sprint_results_race_driver",
                "lap_positions": "uq_lap_positions_race_driver_lap"}[table]
        conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table} ({columns})"))
