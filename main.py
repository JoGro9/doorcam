from fastapi import FastAPI
from sensor import init_sensor
from camera import CameraHandler
import threading
import time

app = FastAPI()
sensor = None
camera = CameraHandler()

def sensor_loop():
    triggered_before = False
    while True:
        triggered = not sensor.is_pressed  # Tür ist offen → Kontakt unterbrochen
        if triggered and not triggered_before:
            print("Sensor ausgelöst – mache Foto...")
            camera.take_picture()
        triggered_before = triggered
        time.sleep(1)

@app.on_event("startup")
def startup_event():
    global sensor
    sensor = init_sensor()
    print("Sensor initialisiert:", sensor)
    threading.Thread(target=sensor_loop, daemon=True).start()

@app.get("/")
def root():
    return {"message": "DoorCam läuft"}

@app.get("/status")
def status():
    return {"sensor_triggered": not sensor.is_pressed}
