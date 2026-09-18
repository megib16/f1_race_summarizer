from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Render (and most hosts) hand out "postgres://", but SQLAlchemy 2.x requires "postgresql://"
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
else:
    DB_PATH = os.path.join(BASE_DIR, "f1_races.db")
    engine = create_engine(f"sqlite:///{DB_PATH}")

SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
