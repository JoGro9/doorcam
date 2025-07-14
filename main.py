# main.py
from fastapi import FastAPI
from sensor import DoorSensor, init_sensor
from camera import CameraHandler
import threading
import time

app = FastAPI()
sensor = DoorSensor()
camera = CameraHandler()

@app.get("/")
def root():
    return {"message": "DoorCam läuft 🎥"}

@app.get("/status")
def status():
    return {"sensor_triggered": sensor.is_triggered()}

def sensor_loop():
    triggered_before = False
    while True:
        triggered = sensor.is_triggered()
        if triggered and not triggered_before:
            print("⏰ Sensor ausgelöst – mache Foto...")
            camera.take_picture()
        triggered_before = triggered
        time.sleep(1)

threading.Thread(target=sensor_loop, daemon=True).start()
