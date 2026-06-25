from fastapi import FastAPI 
from database import SessionLocal 
from models import Race, DriverResult 

app = FastAPI() 
@app.get("/races")
def get_races(): 
    db = SessionLocal()
    races = db.query(Race).all() 
    db.close() 
    return races 

@app.get("/races/{race_id}/results") 
def get_results(race_id: int): 
    db = SessionLocal() 
    results = db.query(DriverResult).filter(DriverResult.race_id == race_id).all() 
    db.close()  
    return results

