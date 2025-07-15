from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from gpiozero import Device, Button
from gpiozero.pins.pigpio import PiGPIOFactory
from camera import CameraHandler
import threading
import cv2
import time
import os
from datetime import datetime, timedelta
import secrets

app = FastAPI()

# Passwortschutz (HTTP Basic Auth)
security = HTTPBasic()
USERNAME = "admin"
PASSWORD = "geheim123"

def check_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Zugang verweigert",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

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

# Entprellung und Status global
letzte_ausloesung = 0
ENTPRELLZEIT = 2  # Sekunden Entprellzeit
tuer_offen = False  # Status, ob Tür aktuell offen ist

def mache_fotos_und_erkenne_gesicht():
    max_fotos = 5
    intervall = 0.5
    erkannte_bilder = []
    alle_bilder = []

    for _ in range(max_fotos):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        bild_pfad = os.path.join(PHOTO_DIR, f"photo_{timestamp}.jpg")

        camera.take_picture(bild_pfad)

        img = cv2.imread(bild_pfad)
        if img is None:
            print(f"Konnte Bild nicht laden: {bild_pfad}")
            continue

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
            break

        time.sleep(intervall)

    if not erkannte_bilder and alle_bilder:
        alle_bilder.sort(key=lambda x: x[1], reverse=True)
        bestes_bild, best_conf = alle_bilder[0]
        print(f"Kein Gesicht erkannt. Bild mit höchster Confidence {best_conf:.2f}: {bestes_bild}")
        erkannte_bilder.append((bestes_bild, best_conf))
        for bild, conf in alle_bilder[1:]:
            if os.path.exists(bild):
                os.remove(bild)
    else:
        erkannte_dateien = set(b[0] for b in erkannte_bilder)
        for bild, conf in alle_bilder:
            if bild not in erkannte_dateien and os.path.exists(bild):
                os.remove(bild)

def sensor_ausgeloest():
    global tuer_offen
    if tuer_offen:
        print("Tür wurde geschlossen – keine Fotos werden gemacht.")
        tuer_offen = False

def sensor_offen():
    global letzte_ausloesung, tuer_offen
    jetzt = time.time()

    if tuer_offen:
        print("Tür ist schon als offen markiert – ignoriere.")
        return

    if jetzt - letzte_ausloesung < ENTPRELLZEIT:
        print("Entprellzeit aktiv – Ignoriere Sensor-Auslösung.")
        return

    letzte_ausloesung = jetzt
    tuer_offen = True
    print("Tür wurde geöffnet – starte Gesichtserkennung")
    mache_fotos_und_erkenne_gesicht()

def init_sensor():
    sensor = Button(17, pull_up=True)
    sensor.when_pressed = sensor_ausgeloest
    sensor.when_released = sensor_offen
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

@app.post("/gallery/clear")
def clear_gallery(_: bool = Depends(check_credentials)):
    gelöscht = 0
    for dateiname in os.listdir(PHOTO_DIR):
        if dateiname.lower().endswith(".jpg"):
            try:
                pfad = os.path.join(PHOTO_DIR, dateiname)
                os.remove(pfad)
                gelöscht += 1
            except Exception as e:
                print(f"Fehler beim Löschen von {dateiname}: {e}")
    print(f"{gelöscht} Bilder gelöscht.")
    return RedirectResponse(url="/gallery", status_code=303)

@app.delete("/gallery")
def delete_gallery(_: bool = Depends(check_credentials)):
    gelöscht = 0
    for dateiname in os.listdir(PHOTO_DIR):
        if dateiname.lower().endswith(".jpg"):
            try:
                pfad = os.path.join(PHOTO_DIR, dateiname)
                os.remove(pfad)
                gelöscht += 1
            except Exception as e:
                print(f"Fehler beim Löschen von {dateiname}: {e}")
    print(f"{gelöscht} Bilder per DELETE gelöscht.")
    return {"status": "ok", "geloescht": gelöscht}

def format_date_from_filename(filename: str) -> str:
    try:
        basename = os.path.basename(filename)
        parts = basename.split('_')
        if len(parts) < 3:
            return "Unbekanntes Datum"
        date_part = parts[1]
        time_part = parts[2]
        dt = datetime.strptime(date_part + time_part, "%Y%m%d%H%M%S")
        return dt.strftime("%A, %d.%m.%Y %H:%M:%S")
    except Exception as e:
        print(f"Fehler beim Parsen des Datums: {e}")
        return "Unbekanntes Datum"

@app.get("/gallery", response_class=HTMLResponse)
def gallery(_: bool = Depends(check_credentials)):
    jetzt = datetime.now()
    drei_tage_zurueck = jetzt - timedelta(days=3)

    bilder = []
    for dateiname in os.listdir(PHOTO_DIR):
        if not dateiname.lower().endswith(".jpg"):
            continue
        try:
            parts = dateiname.split('_')
            if len(parts) < 3:
                continue
            date_part = parts[1]
            time_part = parts[2]
            dt = datetime.strptime(date_part + time_part, "%Y%m%d%H%M%S")
            if dt >= drei_tage_zurueck:
                bilder.append((os.path.join(PHOTO_DIR, dateiname), dt))
        except Exception as e:
            print(f"Fehler beim Parsen des Datums von {dateiname}: {e}")
            continue

    bilder.sort(key=lambda x: x[1], reverse=True)

    datum = jetzt.strftime("%A, %d. %B %Y")
    uhrzeit = jetzt.strftime("%H:%M:%S")

    html = f"""<!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Türkamera Galerie</title>
        <style>
            body {{
                font-family: sans-serif;
                background: #f9f9f9;
                color: #333;
                margin: 0;
                padding: 20px;
            }}
            .gallery {{
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
            }}
            .bild-container {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                padding: 10px;
                max-width: 320px;
                text-align: center;
            }}
            img {{
                max-width: 100%;
                border-radius: 8px;
            }}
            .delete-button {{
                background-color: #e53935;
                color: white;
                font-weight: bold;
                border: none;
                padding: 10px 16px;
                border-radius: 8px;
                cursor: pointer;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>Türkamera Galerie</h1>
        <div>{datum} | <span id="uhrzeit">{uhrzeit}</span></div>
        <form method="post" action="/gallery/clear" onsubmit="return confirm('Wirklich alle Bilder löschen?');">
            <button type="submit" class="delete-button">📸 Galerie löschen</button>
        </form>
        <div class="gallery">"""

    for bild, _ in bilder:
        aufnahmezeit = format_date_from_filename(bild)
        dateiname = os.path.basename(bild)
        html += f"""
            <div class="bild-container">
                <img src='/photo/{dateiname}' alt='Türkamera Bild'/>
                <small>{dateiname}</small>
                <div class="aufnahmezeit">{aufnahmezeit}</div>
            </div>"""

    html += """
        </div>
        <script>
        setInterval(() => {
            const uhr = document.getElementById('uhrzeit');
            if (uhr) uhr.textContent = new Date().toLocaleTimeString('de-DE');
        }, 1000);
        </script>
    </body>
    </html>"""
    return html

