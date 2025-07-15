from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from gpiozero import Device, Button
from gpiozero.pins.pigpio import PiGPIOFactory
from camera import CameraHandler
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import threading
import cv2
import time
import os
from datetime import datetime, timedelta

app = FastAPI()
security = HTTPBasic()

Device.pin_factory = PiGPIOFactory()
camera = CameraHandler()

dnn_model_path = "res10_300x300_ssd_iter_140000.caffemodel"
dnn_config_path = "deploy.prototxt"
net = cv2.dnn.readNetFromCaffe(dnn_config_path, dnn_model_path)

PHOTO_DIR = "temp"
if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)

sensor = None

ENTPRELLZEIT = 2  # Sekunden Mindestabstand
letzte_ausloesung = 0
tuer_offen = None  # Status: True=geschlossen, False=offen, None=unbekannt
entprell_aktiv = False  # Entprell-Log nur einmal zeigen
event_lock = threading.Lock()  # Neu: Für gleichzeitige Events

# Basic Auth Setup
security = HTTPBasic()
USERNAME = "admin"
PASSWORD = "home123"

def check_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Zugang verweigert",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

def check_password(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.password != PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falsches Passwort",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

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
        for bild, _ in alle_bilder[1:]:
            if os.path.exists(bild):
                os.remove(bild)
    else:
        erkannte_set = set(b[0] for b in erkannte_bilder)
        for bild, _ in alle_bilder:
            if bild not in erkannte_set and os.path.exists(bild):
                os.remove(bild)

def sensor_event():
    global letzte_ausloesung, tuer_offen, entprell_aktiv

    with event_lock:  # Nur ein Event gleichzeitig
        jetzt = time.time()

        if jetzt - letzte_ausloesung < ENTPRELLZEIT:
            if not entprell_aktiv:
                print("Sensor ausgelöst, aber Entprellzeit aktiv – Ignoriere.")
                entprell_aktiv = True
            return
        entprell_aktiv = False

        aktueller_status = sensor.is_pressed  # True = geschlossen

        if tuer_offen is None:
            tuer_offen = aktueller_status
            print(f"Initialer Türstatus gesetzt: {'geschlossen' if tuer_offen else 'offen'}")
            return

        if aktueller_status == tuer_offen:
            print("Kein Statuswechsel der Tür, ignoriere.")
            return

        tuer_offen = aktueller_status
        letzte_ausloesung = jetzt

        if not tuer_offen:
            print("Tür wurde geöffnet – starte Gesichtserkennung")
            mache_fotos_und_erkenne_gesicht()
        else:
            print("Tür wurde geschlossen – keine Aktion")

def init_sensor():
    global sensor
    sensor = Button(17, pull_up=True)
    sensor.when_pressed = sensor_event
    sensor.when_released = sensor_event
    print("Magnetsensor ist aktiv.")
    return sensor

def sensor_loop():
    while True:
        time.sleep(1)

@app.on_event("startup")
def startup_event():
    global sensor, tuer_offen
    sensor = init_sensor()
    tuer_offen = sensor.is_pressed
    print(f"Initialer Türstatus beim Start: {'geschlossen' if tuer_offen else 'offen'}")
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

def format_date_from_filename(filename: str) -> str:
    try:
        basename = os.path.basename(filename)
        parts = basename.split('_')
        if len(parts) < 3:
            return "Unbekanntes Datum"
        dt = datetime.strptime(parts[1] + parts[2], "%Y%m%d%H%M%S")
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
            .aufnahmezeit {{
                font-size: 0.9em;
                color: #555;
                margin-top: 4px;
                font-style: italic;
            }}
            #delete-btn {{
                margin-bottom: 20px;
                background: #e53935;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 1em;
                border-radius: 6px;
                cursor: pointer;
            }}
            #delete-btn:hover {{
                background: #d32f2f;
            }}
        </style>
    </head>
    <body>
        <h1>Türkamera Galerie</h1>
        <div id="datetime">{datum} | <span id="uhrzeit">{uhrzeit}</span></div>
        <button id="delete-btn">Galerie leeren</button>
        <div class="gallery">
    """

    for bild, _ in bilder:
        aufnahmezeit = format_date_from_filename(bild)
        dateiname = os.path.basename(bild)
        html += f"""
            <div class="bild-container">
                <img src='/photo/{dateiname}' alt='Türkamera Bild'/>
                <small>{dateiname}</small>
                <div class="aufnahmezeit">{aufnahmezeit}</div>
            </div>
        """

    html += """
        </div>
        <script>
            function updateTime() {
                const uhrzeitElem = document.getElementById('uhrzeit');
                const now = new Date();
                uhrzeitElem.textContent = now.toLocaleTimeString('de-DE');
            }
            setInterval(updateTime, 1000);

            document.getElementById("delete-btn").addEventListener("click", async () => {
                const password = prompt("Bitte Admin-Passwort eingeben:");
                if (!password) return;

                const res = await fetch("/gallery/clear", {
                    method: "DELETE",
                    headers: {
                        "Authorization": "Basic " + btoa("admin:" + password)
                    }
                });

                const json = await res.json();
                alert(json.message || json.error);
                if (res.ok) location.reload();
            });
        </script>
    </body>
    </html>
    """
    return html


@app.delete("/gallery/clear")
def clear_gallery(auth: bool = Depends(check_password)):
    try:
        for filename in os.listdir(PHOTO_DIR):
            if filename.lower().endswith(".jpg"):
                os.remove(os.path.join(PHOTO_DIR, filename))
        return {"message": "Galerie wurde geleert."}
    except Exception as e:
        return {"error": f"Fehler beim Leeren der Galerie: {e}"}
