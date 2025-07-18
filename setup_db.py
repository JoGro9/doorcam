# setup_db.py
import sqlite3

conn = sqlite3.connect("faces.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS personen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    encoding BLOB,
    bild BLOB
)
""")

conn.commit()
conn.close()
