from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ---------------- DATABASE CONNECTION ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "parking.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- HOME ----------------
@app.route('/')
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template('home.html')


# ---------------- REGISTER (ADMIN) ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        conn.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, password)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    vehicles = conn.execute("SELECT * FROM vehicles").fetchall()
    slots = conn.execute("SELECT * FROM parking_slots").fetchall()
    conn.close()

    return render_template(
        "dashboard.html",
        vehicles=vehicles,
        slots=slots,
        username=session["username"]
    )

# ---------------- VEHICLE ENTRY ----------------
@app.route("/vehicle-entry", methods=["GET", "POST"])
def vehicle_entry():
    if request.method == "POST":
        vehicle_no = request.form["vehicle_no"]
        owner_name = request.form["owner_name"]
        entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()

        # Find first available slot
        slot = conn.execute(
            "SELECT slot_id FROM parking_slots WHERE status = 'Available' LIMIT 1"
        ).fetchone()

        if slot is None:
            conn.close()
            return "No parking slots available"

        slot_id = slot["slot_id"]

        # Insert vehicle
        conn.execute(
            """
            INSERT INTO vehicles (vehicle_no, owner_name, slot_id, entry_time)
            VALUES (?, ?, ?, ?)
            """,
            (vehicle_no, owner_name, slot_id, entry_time)
        )

        # Mark slot as occupied
        conn.execute(
            "UPDATE parking_slots SET status = 'Occupied' WHERE slot_id = ?",
            (slot_id,)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("vehicle_entry.html")


# ---------------- VEHICLE EXIT ----------------
@app.route("/vehicle-exit", methods=["GET", "POST"])
def vehicle_exit():
    if request.method == "POST":
        vehicle_no = request.form["vehicle_no"]
        exit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()

        vehicle = conn.execute("""
            SELECT v.vehicle_id, v.entry_time, v.slot_id, s.slot_name
            FROM vehicles v
            JOIN parking_slots s ON v.slot_id = s.slot_id
            WHERE v.vehicle_no = ? AND v.exit_time IS NULL
        """, (vehicle_no,)).fetchone()

        if vehicle is None:
            conn.close()
            return render_template(
                "vehicle_exit.html",
                error="Vehicle not found or already exited"
            )

        # Fee calculation (₹20 per hour)
        entry = datetime.strptime(vehicle["entry_time"], "%Y-%m-%d %H:%M:%S")
        exit_ = datetime.strptime(exit_time, "%Y-%m-%d %H:%M:%S")
        hours = max(1, int((exit_ - entry).total_seconds() // 3600 + 1))
        fee = hours * 20

        # Update vehicle
        conn.execute("""
            UPDATE vehicles
            SET exit_time = ?, fee = ?
            WHERE vehicle_id = ?
        """, (exit_time, fee, vehicle["vehicle_id"]))

        # Free slot
        conn.execute("""
            UPDATE parking_slots
            SET status = 'Available'
            WHERE slot_id = ?
        """, (vehicle["slot_id"],))

        conn.commit()
        conn.close()

        return render_template(
            "vehicle_exit.html",
            success=True,
            vehicle_no=vehicle_no,
            slot_name=vehicle["slot_name"],
            fee=fee
        )

    return render_template("vehicle_exit.html")

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True)
