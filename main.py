# main.py
from fastapi import FastAPI
from sensor import DoorSensor
import threading
import time

app = FastAPI()
sensor = DoorSensor()

@app.get("/")
def root():
    return {"message": "DoorCam läuft 🎥"}

@app.get("/status")
def status():
    return {"sensor_triggered": sensor.is_triggered()}

def sensor_loop():
    while True:
        if sensor.is_triggered():
            print("⏰ Ereignis erkannt – hier könnte ein Foto gemacht werden!")
        time.sleep(1)

threading.Thread(target=sensor_loop, daemon=True).start()
