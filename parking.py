import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "parking.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -------- USERS TABLE --------
cursor.execute("""
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# -------- PARKING SLOTS TABLE --------
cursor.execute("""
CREATE TABLE parking_slots (
    slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_name TEXT UNIQUE NOT NULL,
    status TEXT CHECK(status IN ('Available', 'Occupied')) DEFAULT 'Available'
)
""")

# -------- VEHICLES TABLE --------
cursor.execute("""
CREATE TABLE vehicles (
    vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_no TEXT NOT NULL,
    owner_name TEXT NOT NULL,
    slot_id INTEGER,
    entry_time DATETIME,
    exit_time DATETIME,
    fee INTEGER,
    FOREIGN KEY (slot_id) REFERENCES parking_slots(slot_id)
)
""")

conn.commit()
conn.close()

print("✅ Fresh database created with all tables")
