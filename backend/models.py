from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Race(Base):
    __tablename__ = "races"
    race_id = Column(Integer, primary_key=True)
    name = Column(String)
    location = Column(String)
    date = Column(String)
    round = Column(Integer)
    total_laps = Column(Integer)
    summary = Column(String)
    fastest_lap_driver = Column(String)
    fastest_lap_time = Column(String)
    fastest_lap_number = Column(Integer) 
    fastest_lap_team = Column(String) 
    air_temp = Column(Float)
    track_temp = Column(Float)
    rainfall = Column(String)

class DriverResult(Base):
    __tablename__ = "results"
    driver_id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey("races.race_id"))
    position = Column(Integer)
    grid_position = Column(Integer)
    full_name = Column(String)
    abbreviation = Column(String)
    team = Column(String)
    time = Column(String)
    fastest_lap = Column(String)

class LapPosition(Base):
    __tablename__ = "lap_positions"
    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey("races.race_id"))
    driver = Column(String)
    lap_number = Column(Integer)
    position = Column(Integer) 

class PitStop(Base):
    __tablename__ = "pitstops"
    id = Column(Integer, primary_key = True)
    race_id = Column(Integer, ForeignKey("races.race_id"))
    driver = Column(String)
    lap_number = Column(Integer)
    old_compound = Column(String)
    new_compound = Column(String)

class SprintResult(Base):
    __tablename__ = "sprint_results"
    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey("races.race_id"))
    position = Column(Integer)
    full_name = Column(String)
    team = Column(String)


class RaceMeta(Base):
    """Operational bookkeeping per race, kept out of `races` so it needs no ALTER TABLE.

    A race with no row here has a legacy summary (written before prompt versions
    were tracked) and no recorded sprint attempts.
    """
    __tablename__ = "race_meta"
    race_id = Column(Integer, ForeignKey("races.race_id"), primary_key=True)
    summary_prompt_version = Column(Integer)
    sprint_attempts = Column(Integer, default=0)
    sprint_last_attempt = Column(String)  # ISO date


class CircuitMap(Base):
    """Render-ready circuit geometry per race (processed from MultiViewer data at ingest).

    `status` is "available" or "unavailable"; unavailable rows record why, so the
    lookup is not repeated on every run. Layouts change between years, so the map
    is stored per race rather than per circuit.
    """
    __tablename__ = "circuit_maps"
    race_id = Column(Integer, ForeignKey("races.race_id"), primary_key=True)
    status = Column(String, nullable=False)
    reason = Column(String)
    circuit_key = Column(Integer)
    source = Column(String)
    data = Column(Text)  # JSON from circuit.build_circuit_map
    fetched_at = Column(String)  # ISO date


def get_or_create_meta(db, race_id):
    meta = db.get(RaceMeta, race_id)
    if meta is None:
        meta = RaceMeta(race_id=race_id, sprint_attempts=0)
        db.add(meta)
    return meta
