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
        



#Base — one line: Base = declarative_base() — this is what all your table classes inherit from

#Race class — columns: id (Integer, primary key), name, location, date (all String), round, total_laps (both Integer), summary (String — for the AI text later)

#DriverResult class — columns: id (Integer, primary key), race_id (Integer, ForeignKey linking to races.id), position (Integer), full_name, team, time (all String)

#A column looks like this:


#name = Column(String)
#id = Column(Integer, primary_key=True)
#race_id = Column(Integer, ForeignKey("races.id"))
