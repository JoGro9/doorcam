# setup_db.py
import sqlite3

conn = sqlite3.connect("faces.db")
cursor = conn.cursor()

cursor.execute("ALTER TABLE personen ADD COLUMN encoding TEXT")
cursor.execute("""
CREATE TABLE IF NOT EXISTS personen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    bild TEXT
)
""")

conn.commit()
conn.close()
