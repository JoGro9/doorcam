from fastapi import FastAPI
from gpiozero import Device, Button
from gpiozero.pins.pigpio import PiGPIOFactory
from camera import CameraHandler
import threading
import cv2
import time
import os
from datetime import datetime

app = FastAPI()

# Setup für GPIO
Device.pin_factory = PiGPIOFactory()

# Kamera initialisieren
camera = CameraHandler()

# Gesichtserkennung vorbereiten
face_cascade = cv2.CascadeClassifier('haarcascades/haarcascade_frontalface_default.xml')

sensor = None  # Wird beim Startup initialisiert


def mache_fotos_und_erkenne_gesicht():
    max_fotos = 5
    intervall = 0.5  # Sekunden
    gesicht_gefunden = False

    if not os.path.exists("temp"):
        os.makedirs("temp")

    for i in range(max_fotos):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        bild_pfad = f"temp/photo_{timestamp}.jpg"

        # Foto aufnehmen
        camera.take_picture(bild_pfad)

        # Bild laden und verarbeiten
        img = cv2.imread(bild_pfad)
        if img is None:
            print(f"Konnte Bild nicht laden: {bild_pfad}")
            continue

        graustufen = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gesichter = face_cascade.detectMultiScale(graustufen, scaleFactor=1.1, minNeighbors=5)

        if len(gesichter) > 0:
            print(f"Gesicht erkannt auf Foto {bild_pfad}")
            gesicht_gefunden = True
            break
        else:
            os.remove(bild_pfad)

        time.sleep(intervall)

    if not gesicht_gefunden:
        print("Kein Gesicht erkannt.")


def sensor_ausgeloest():
    print("Tür wurde geöffnet – Sensor ausgelöst.")
    mache_fotos_und_erkenne_gesicht()


def init_sensor():
    sensor = Button(17, pull_up=True)
    sensor.when_released = sensor_ausgeloest
    print("Magnetsensor ist aktiv.")
    return sensor


def sensor_loop():
    # Optional: Polling-Loop zur zusätzlichen Logik
    while True:
        time.sleep(1)


@app.on_event("startup")
def startup_event():
    global sensor
    sensor = init_sensor()
    threading.Thread(target=sensor_loop, daemon=True).start()
    print("System gestartet.")


@app.get("/")
def root():
    return {"message": "DoorCam läuft"}
