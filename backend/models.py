from sqlalchemy import Column, Integer, String, Float, ForeignKey 
from sqlalchemy.orm import declarative_base 

Base = declarative_base() 

class Race(Base): 
        __tablename__ = "races"
        race_id = Column(Integer, primary_key = True) 
        name = Column(String) 
        location = Column(String) 
        date = Column(String) 
        round = Column(Integer) 
        total_laps = Column(Integer) 
        summary = Column(String) 

class DriverResult(Base): 
        __tablename__ = "results"
        driver_id = Column(Integer, primary_key = True) 
        race_id = Column(Integer, ForeignKey("races.race_id")) 
        position = Column(Integer) 
        full_name = Column(String) 
        team = Column(String) 
        time = Column(String)         
        

