from gpiozero import Device, Button
from gpiozero.pins.pigpio import PiGPIOFactory
import cv2
import time
import os
from datetime import datetime
from camera import CameraHandler  # Deine Kamera-Klasse

# Pin-Factory global setzen
Device.pin_factory = PiGPIOFactory()

# Kamera-Handler initialisieren
camera = CameraHandler()

# Gesichtserkennung vorbereiten
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def mache_fotos_und_erkenne_gesicht():
    max_fotos = 5
    intervall = 0.5  # Sekunden
    gesicht_gefunden = False
    
    # Temp-Ordner sicherstellen
    if not os.path.exists("temp"):
        os.makedirs("temp")
    
    for i in range(max_fotos):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        bild_pfad = f"temp/photo_{timestamp}.jpg"
        
        # Foto aufnehmen
        camera.take_picture(bild_pfad)
        
        # Bild laden und in Graustufen umwandeln
        img = cv2.imread(bild_pfad)
        graustufen = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Gesichter erkennen
        gesichter = face_cascade.detectMultiScale(graustufen, scaleFactor=1.1, minNeighbors=5)
        
        if len(gesichter) > 0:
            print(f"Gesicht erkannt auf Foto {bild_pfad}")
            # Foto behalten (kannst es ggf. noch verschieben oder umbenennen)
            gesicht_gefunden = True
            break
        else:
            # Kein Gesicht: Foto löschen
            os.remove(bild_pfad)
        
        time.sleep(intervall)
    
    if not gesicht_gefunden:
        print("Kein Gesicht erkannt.")

def sensor_ausgeloest():
    print("Tür wurde geöffnet – Sensor ausgelöst.")
    mache_fotos_und_erkenne_gesicht()

def init_sensor():
    # pull_up=True: Pin ist HIGH, wenn Sensorkontakt offen ist (Tür offen)
    sensor = Button(17, pull_up=True)
    sensor.when_released = sensor_ausgeloest  # Event: Tür öffnet (Kontakt trennt)
    print("Magnetsensor ist aktiv.")
    return sensor

# Wenn du den Sensor sofort initialisieren willst (z.B. beim Import)
# sensor = init_sensor()
