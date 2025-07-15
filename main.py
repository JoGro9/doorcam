from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
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

# DNN-Gesichtserkennung vorbereiten
dnn_model_path = "res10_300x300_ssd_iter_140000.caffemodel"
dnn_config_path = "deploy.prototxt"
net = cv2.dnn.readNetFromCaffe(dnn_config_path, dnn_model_path)

# Foto-Speicherort
PHOTO_DIR = "temp"
if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)

sensor = None  # Wird beim Startup gesetzt


def mache_fotos_und_erkenne_gesicht():
    max_fotos = 5
    intervall = 0.5
    gesicht_gefunden = False

    for i in range(max_fotos):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        bild_pfad = os.path.join(PHOTO_DIR, f"photo_{timestamp}.jpg")

        # Foto aufnehmen
        camera.take_picture(bild_pfad)

        # Bild laden
        img = cv2.imread(bild_pfad)
        if img is None:
            print(f"Konnte Bild nicht laden: {bild_pfad}")
            continue

        h, w = img.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 1.0,
                                     (300, 300), (104.0, 177.0, 123.0))
        net.setInput(blob)
        detections = net.forward()

        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:
                print(f"Gesicht erkannt auf Foto {bild_pfad} (Confidence: {confidence:.2f})")
                gesicht_gefunden = True
                break

        if gesicht_gefunden:
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


@app.get("/photo/{filename}")
def get_photo(filename: str):
    pfad = os.path.join(PHOTO_DIR, filename)
    if os.path.exists(pfad):
        return FileResponse(pfad, media_type="image/jpeg")
    return {"error": "Foto nicht gefunden"}


@app.get("/gallery", response_class=HTMLResponse)
def gallery():
    bilder = sorted(
        [f for f in os.listdir(PHOTO_DIR) if f.endswith(".jpg")],
        reverse=True
    )

    html = "<h1>Türkamera Galerie</h1><div style='display:flex; flex-wrap:wrap;'>"
    for bild in bilder:
        html += f"""
            <div style='margin:10px'>
                <img src='/photo/{bild}' width='320' style='border:1px solid #ccc'/><br>
                <small>{bild}</small>
            </div>
        """
    html += "</div>"
    return html
