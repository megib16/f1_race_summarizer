from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "f1_races.db")

engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(bind = engine) 
Base.metadata.create_all(engine)