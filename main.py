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

# Liste für erkannte Gesichter mit Confidence (filename, confidence)
erkannte_bilder = []
# Liste für alle gemachten Bilder (filename, confidence)
alle_bilder = []


def mache_fotos_und_erkenne_gesicht():
    max_fotos = 5
    intervall = 0.5
    gesicht_gefunden = False
    erkannte_bilder.clear()
    alle_bilder.clear()

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

        max_confidence = 0
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > max_confidence:
                max_confidence = confidence

        alle_bilder.append((bild_pfad, max_confidence))

        if max_confidence > 0.5:
            print(f"Gesicht erkannt auf Foto {bild_pfad} (Confidence: {max_confidence:.2f})")
            erkannte_bilder.append((bild_pfad, max_confidence))
            gesicht_gefunden = True
            # Hier abbrechen, da Gesicht gefunden
            break
        else:
            # Kein Gesicht mit Confidence >0.5 erkannt, Bild speichern erstmal
            # Löschen nicht sofort, da wir Bild mit bestmöglicher Übereinstimmung evtl. brauchen
            pass

        time.sleep(intervall)

    # Wenn kein Gesicht erkannt wurde, suche Bild mit höchster Confidence
    if not gesicht_gefunden and alle_bilder:
        alle_bilder.sort(key=lambda x: x[1], reverse=True)  # absteigend sortieren
        bestes_bild, best_conf = alle_bilder[0]
        print(f"Kein Gesicht erkannt. Speichere Bild mit höchster Confidence {best_conf:.2f}: {bestes_bild}")
        # Alle Bilder außer bestes Bild löschen
        for bild, conf in alle_bilder[1:]:
            if os.path.exists(bild):
                os.remove(bild)
        erkannte_bilder.append((bestes_bild, best_conf))
    else:
        # Wenn Gesicht erkannt, lösche alle Bilder außer erkannte
        for bild, conf in alle_bilder:
            if (bild, conf) not in erkannte_bilder:
                if os.path.exists(bild):
                    os.remove(bild)


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
    # Zeige nur Bilder mit erkannter positiver Gesichtserkennung ODER das beste Bild bei keinem Treffer
    bilder = [os.path.basename(bild[0]) for bild in erkannte_bilder if os.path.exists(bild[0])]

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
