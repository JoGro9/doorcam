from fastapi import FastAPI
from sensor import init_sensor

app = FastAPI()

@app.on_event("startup")
def startup_event():
    print("🔧 Starte FastAPI-Anwendung...")
    init_sensor()

@app.get("/")
def read_root():
    return {"message": "Doorcam läuft"} 
