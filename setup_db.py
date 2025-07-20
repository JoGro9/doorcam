# setup_db.py
import sqlite3

conn = sqlite3.connect("faces.db")
cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS personen")
cursor.execute("""
CREATE TABLE IF NOT EXISTS personen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    bild TEXT,
    encoding TEXT
)
""")

conn.commit()
conn.close()
