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

# Entprellung global
letzte_ausloesung = None
ENTPRELLZEIT = 2  # Sekunden


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
    global letzte_ausloesung
    jetzt = time.time()
    if letzte_ausloesung is None or (jetzt - letzte_ausloesung) > ENTPRELLZEIT:
        letzte_ausloesung = jetzt
        print("Tür wurde geöffnet – Sensor ausgelöst.")
        mache_fotos_und_erkenne_gesicht()
    else:
        print("Sensor ausgelöst, aber Entprellzeit aktiv - Ignoriere.")


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
    bilder = [os.path.basename(bild[0]) for bild in erkannte_bilder if os.path.exists(bild[0])]

    now = datetime.now()
    datum = now.strftime("%A, %d. %B %Y")
    uhrzeit = now.strftime("%H:%M:%S")

    html = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Türkamera Galerie</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Text:wght@400;600&display=swap');
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Oxygen,
                    Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
                background: #f9f9f9;
                color: #333;
                margin: 0;
                padding: 20px;
            }}
            h1 {{
                font-weight: 600;
                color: #111;
                margin-bottom: 5px;
            }}
            #datetime {{
                color: #666;
                margin-bottom: 20px;
                font-size: 1.1em;
                font-weight: 400;
            }}
            .gallery {{
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                justify-content: flex-start;
            }}
            .bild-container {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                padding: 10px;
                max-width: 320px;
                text-align: center;
                transition: box-shadow 0.3s ease;
            }}
            .bild-container:hover {{
                box-shadow: 0 8px 30px rgba(0,0,0,0.15);
            }}
            img {{
                max-width: 100%;
                border-radius: 8px;
                user-select: none;
            }}
            small {{
                display: block;
                margin-top: 8px;
                color: #888;
                font-size: 0.85em;
                font-family: monospace;
                word-break: break-word;
            }}
        </style>
    </head>
    <body>
        <h1>Türkamera Galerie</h1>
        <div id="datetime">{datum} | <span id="uhrzeit">{uhrzeit}</span></div>
        <div class="gallery">
    """

    for bild in bilder:
        html += f"""
            <div class="bild-container">
                <img src='/photo/{bild}' alt='Türkamera Bild'/>
                <small>{bild}</small>
            </div>
        """
    html += """
        </div>

        <script>
        // Uhrzeit live aktualisieren
        function updateTime() {
            const uhrzeitSpan = document.getElementById('uhrzeit');
            const jetzt = new Date();
            const stunden = String(jetzt.getHours()).padStart(2, '0');
            const minuten = String(jetzt.getMinutes()).padStart(2, '0');
            const sekunden = String(jetzt.getSeconds()).padStart(2, '0');
            uhrzeitSpan.textContent = `${stunden}:${minuten}:${sekunden}`;
        }
        setInterval(updateTime, 1000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
