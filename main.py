from fastapi import FastAPI
from sensor import DoorSensor, init_sensor
from camera import CameraHandler
import threading
import time

app = FastAPI()
sensor = None  # Wird erst nach init_sensor gesetzt
camera = CameraHandler()

def sensor_loop():
    triggered_before = False
    while True:
        triggered = sensor.is_pressed
        if triggered and not triggered_before:
            print("Sensor ausgelöst – mache Foto...")
            camera.take_picture()
        triggered_before = triggered
        time.sleep(1)

@app.on_event("startup")
def startup_event():
    global sensor
    init_sensor()      # Sensor initialisieren (setzt DoorSensor)
    sensor = DoorSensor
    threading.Thread(target=sensor_loop, daemon=True).start()

@app.get("/")
def root():
    return {"message": "DoorCam läuft"}

@app.get("/status")
def status():
    return {"sensor_triggered": sensor.is_pressed}
