from sqlalchemy import Column, Integer, String, Float, ForeignKey
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
    air_temp = Column(Float)
    track_temp = Column(Float)
    rainfall = Column(String)

class DriverResult(Base):
    __tablename__ = "results"
    driver_id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey("races.race_id"))
    position = Column(Integer)
    full_name = Column(String)
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
    lap_numer = Column(Integer)
    old_compound = Column(String) 
    new_compound = Column(String)    
