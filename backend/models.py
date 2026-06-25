from sqlalchemy import Column, Integer, String, Float, ForeignKey 
from sqlalchemy.orm import DeclarativeBase 

Base = declarative_base()
#Base — one line: Base = declarative_base() — this is what all your table classes inherit from

#Race class — columns: id (Integer, primary key), name, location, date (all String), round, total_laps (both Integer), summary (String — for the AI text later)

#DriverResult class — columns: id (Integer, primary key), race_id (Integer, ForeignKey linking to races.id), position (Integer), full_name, team, time (all String)

#A column looks like this:


#name = Column(String)
#id = Column(Integer, primary_key=True)
#race_id = Column(Integer, ForeignKey("races.id"))
