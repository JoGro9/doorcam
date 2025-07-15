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

# DNN-Modell für Gesichtserkennung laden
prototxt_path = "models/deploy.prototxt"
model_path = "models/res10_300x300_ssd_iter_140000.caffemodel"
net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)

# Foto-Speicherort
PHOTO_DIR = "temp"
if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)

sensor = None  # Wird beim Startup gesetzt


def mache_fotos_und_erkenne_gesicht():
    max_fotos = 5
    intervall = 0.5
    best_confidence = 0.0
    best_path = None

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

        found = False
        for j in range(detections.shape[2]):
            confidence = detections[0, 0, j, 2]
            if confidence > 0.5:
                print(f"✅ Gesicht erkannt mit {confidence:.2f} auf {bild_pfad}")
                found = True
                break
            elif confidence > best_confidence:
                best_confidence = confidence
                best_path = bild_pfad

        if found:
            break
        else:
            time.sleep(intervall)

    if not found:
        if best_path:
            print(f"⚠️ Kein klares Gesicht erkannt, bestes war {best_confidence:.2f}, Bild behalten: {best_path}")
        else:
            print("❌ Kein Gesicht erkannt und kein brauchbares Bild.")


def sensor_ausgeloest():
    print("Tür geöffnet erkannt.")
    mache_fotos_und_erkenne_gesicht()


def init_sensor():
    sensor = Button(17, pull_up=True)

    def check_status():
        if not sensor.is_pressed:
            sensor_ausgeloest()

    sensor.when_released = check_status  # Reagiere nur beim Öffnen
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
