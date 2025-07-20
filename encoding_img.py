import sqlite3
import face_recognition
import os
import json  # Zum Speichern des Encodings als JSON-String

DB_PATH = "faces.db"

def encode_faces_and_update_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, bild FROM personen")
    rows = cursor.fetchall()

    for person_id, bild_pfad in rows:
        if not os.path.exists(bild_pfad):
            print(f"Bild nicht gefunden: {bild_pfad} (ID: {person_id})")
            continue

        # Bild laden
        image = face_recognition.load_image_file(bild_pfad)
        encodings = face_recognition.face_encodings(image)

        if len(encodings) == 0:
            print(f"Kein Gesicht gefunden im Bild {bild_pfad} (ID: {person_id})")
            continue

        encoding = encodings[0]
        # Encoding als JSON speichern, weil es ein numpy array ist
        encoding_json = json.dumps(encoding.tolist())

        # In DB updaten
        cursor.execute("UPDATE personen SET encoding = ? WHERE id = ?", (encoding_json, person_id))
        print(f"Encoding für ID {person_id} aktualisiert.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    encode_faces_and_update_db()
