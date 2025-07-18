import cv2
import os
import time
from datetime import datetime

face_cascade = cv2.CascadeClassifier('haarcascades/haarcascade_frontalface_default.xml')


def erkenne_gesicht_und_speichere_foto(camera):
    max_fotos = 5
    intervall = 0.5  # Sekunden

    # Ordner für Fotos anlegen
    if not os.path.exists("photos"):
        os.makedirs("photos")

    for _ in range(max_fotos):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        pfad = f"photos/photo_{timestamp}.jpg"

        camera.take_picture(pfad)

        img = cv2.imread(pfad)
        graustufen = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gesichter = face_cascade.detectMultiScale(graustufen, scaleFactor=1.1, minNeighbors=5)

        if len(gesichter) > 0:
            print(f"Gesicht erkannt und Foto gespeichert: {pfad}")
            return
        else:
            os.remove(pfad)

        time.sleep(intervall)

    print("Kein Gesicht erkannt.")
