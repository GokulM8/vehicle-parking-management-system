import sqlite3

# Create and connect to database
conn = sqlite3.connect("parking.db")
cursor = conn.cursor()

# Admin users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# Vehicle parking table
cursor.execute("""
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_no TEXT UNIQUE NOT NULL,
    vehicle_type TEXT NOT NULL,
    entry_time TEXT NOT NULL,
    exit_time TEXT
)
""")

conn.commit()
conn.close()

print("✅ parking.db created successfully")
