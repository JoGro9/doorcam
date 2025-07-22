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
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.staticfiles import StaticFiles
import sqlite3
import face_recognition
import numpy as np
import json
import requests




app = FastAPI()
security = HTTPBasic()

Device.pin_factory = PiGPIOFactory()
camera = CameraHandler()

dnn_model_path = "res10_300x300_ssd_iter_140000.caffemodel"
dnn_config_path = "deploy.prototxt"
net = cv2.dnn.readNetFromCaffe(dnn_config_path, dnn_model_path)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/profil_img", StaticFiles(directory="profil_img"), name="profil_img")

API_KEY = "b8244bb2-df06-4e86-9aa7-771a0740b547"
DEVICE_MACS = [
        "22:18:D0:C9:07:C7:54:7C",
        "B0:B5:D0:C9:07:C7:A8:20"   # Schlafzimmer
    ]
DEVICE_MODEL = "H6008"


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
            erkanntes_profil = encode_face(bild_pfad)
            id = match_face(erkanntes_profil)
            print(f"Match gefunden {id}")
            ergebnis = govee_set_color(id)
            print(ergebnis)
            break

        time.sleep(intervall)

    if erkannte_bilder:
        # Nur das erkannte Bild behalten, Rest löschen
        bestes_bild = erkannte_bilder[0][0]
        for bild, _ in alle_bilder:
            if bild != bestes_bild and os.path.exists(bild):
                os.remove(bild)
        print(f"Gespeichertes Bild mit erkanntem Gesicht: {bestes_bild}")
    else:
        # Kein Gesicht erkannt – alle Bilder löschen
        for bild, _ in alle_bilder:
            if os.path.exists(bild):
                os.remove(bild)
        print("Kein Gesicht erkannt – alle Bilder gelöscht.")

def govee_set_color(id):
    conn = sqlite3.connect("faces.db")
    cursor = conn.cursor()
    cursor.execute("SELECT r, g, b FROM personen WHERE id = ?", (id,))
    daten = cursor.fetchone()
    conn.close()

    if daten is not None:
        r,g,b = daten

    url = "https://developer-api.govee.com/v1/devices/control"
    headers = {
        "Govee-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    for mac in DEVICE_MACS:
        payload = {
            "device": mac,
            "model": DEVICE_MODEL,
            "cmd": {
                "name": "color",
                "value": {"r": r, "g": g, "b": b}
            }
        }
        response = requests.put(url, json=payload, headers=headers)
        print(f"{mac}: {response.json()}")

def sende_benachrichtigung(id):
    conn = sqlite3.connect("faces.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM personen WHERE id = ?", (id,))
    daten = cursor.fetchone()
    conn.close()

    if daten is not None:
        name = daten
    try:
        url = f"http://192.168.178.40:8000/notify/{name}"
        response = requests.get(url)
        print("Benachrichtigung gesendet:", response.json())
    except Exception as e:
        print("Fehler beim Senden der Benachrichtigung:", e)

def encode_face(bild_pfad):
    print("🔍 Vergleiche erkanntes Gesicht mit Datenbank")
    
    # Absoluten Pfad zum Bild berechnen
    image_path = os.path.join(os.getcwd(), bild_pfad)
    print("📸 Bildpfad:", image_path)

    try:
        # Bild laden
        image = face_recognition.load_image_file(image_path)

        # Gesichts-Encodings extrahieren
        encodings = face_recognition.face_encodings(image)

        # Prüfen, ob ein Gesicht erkannt wurde
        if not encodings:
            print("❌ Kein Gesicht erkannt.")
            return None

        # Erstes erkanntes Gesicht verwenden
        encoding = encodings[0]

        # Encoding in JSON-String umwandeln
        encoding_json = json.dumps(encoding.tolist())

        print("✅ Gesicht erfolgreich encodiert.")
        return encoding_json

    except Exception as e:
        print("⚠️ Fehler beim Verarbeiten des Bildes:", str(e))
        return None

def match_face(erkanntes_profil_json):
    # erkanntes_profil JSON-String in numpy array umwandeln
    erkanntes_profil = np.array(json.loads(erkanntes_profil_json), dtype=np.float32)

    # Datenbankverbindung öffnen und Daten auslesen
    conn = sqlite3.connect("faces.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, bild, encoding FROM personen")
    daten = cursor.fetchall()
    conn.close()

    personen = [
        {"id": row[0], "name": row[1], "bild": row[2], "db_encode": row[3]}
        for row in daten
    ]

    # Gesichter vergleichen
    for person in personen:
        encoding_db = np.array(json.loads(person["db_encode"]), dtype=np.float32)
        match = face_recognition.compare_faces([encoding_db], erkanntes_profil)
        if match[0]:
            print("Gesichtsübereinstimmung in Datenbank gefunden")
            return person["id"]

    print("Kein passendes Gesicht in der Datenbank gefunden")
    return None
    

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
def gallery(request: Request, _: bool = Depends(check_credentials)):
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
                aufnahmezeit = format_date_from_filename(dateiname)
                bilder.append((os.path.join(PHOTO_DIR, dateiname), dateiname, aufnahmezeit))
        except Exception as e:
            print(f"Fehler beim Parsen des Datums von {dateiname}: {e}")
            continue

    bilder.sort(key=lambda x: x[0], reverse=True)  # sortiere nach Pfad (Datum)

    datum = jetzt.strftime("%A, %d. %B %Y")
    uhrzeit = jetzt.strftime("%H:%M:%S")

    return templates.TemplateResponse("gallery.html", {
        "request": request,
        "datum": datum,
        "uhrzeit": uhrzeit,
        "bilder": bilder,
    })

@app.get("/personen")
def show_db(request: Request):
    try:
        conn = sqlite3.connect("faces.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, bild FROM personen")
        daten = cursor.fetchall()
        conn.close()

        personen = [
            {"id": row[0], "name": row[1], "bild": row[2]}
            for row in daten        
        ]
        return templates.TemplateResponse("db.html", {
            "request": request,
            "personen": personen
        })

    except Exception as e: 
        return {"error": f"Fehler beim laden der Datenbank: {e}"}


@app.delete("/gallery/clear")
def clear_gallery(auth: bool = Depends(check_password)):
    try:
        for filename in os.listdir(PHOTO_DIR):
            if filename.lower().endswith(".jpg"):
                os.remove(os.path.join(PHOTO_DIR, filename))
        return {"message": "Galerie wurde geleert."}
    except Exception as e:
        return {"error": f"Fehler beim Leeren der Galerie: {e}"}

@app.get("/notify/{name}")
def notify(name: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"📸 {name} ist um {now} nach Hause gekommen."

    response = requests.post("https://ntfy.sh/doorcam-hebc647hdy67hsn6h4b7d-kalrgdypp",  # 'doorcam' ist dein Topic
                             data=message.encode('utf-8'),
                             headers={"Title": "Türkamera", "Priority": "high"})

    return {"status": "ok", "message": message}