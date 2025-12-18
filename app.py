from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ---------------- DATABASE CONNECTION ----------------
def get_db():
    conn = sqlite3.connect("parking.db")   # 🔁 changed DB name
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- HOME / LOGIN PAGE ----------------
@app.route('/')
def home():
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

        print("LOGIN ATTEMPT:", email)

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            print("LOGIN SUCCESS")
            return redirect(url_for("dashboard"))
        else:
            print("LOGIN FAILED")
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ---------------- VEHICLE ENTRY ----------------
@app.route("/vehicle-entry", methods=["GET", "POST"])
def vehicle_entry():
    if request.method == "POST":
        vehicle_no = request.form["vehicle_no"]
        vehicle_type = request.form["vehicle_type"]
        entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        conn.execute(
            "INSERT INTO vehicles (vehicle_no, vehicle_type, entry_time) VALUES (?, ?, ?)",
            (vehicle_no, vehicle_type, entry_time)
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
        conn.execute(
            "UPDATE vehicles SET exit_time = ? WHERE vehicle_no = ?",
            (exit_time, vehicle_no)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("vehicle_exit.html")


# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True)
