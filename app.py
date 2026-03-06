from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
import sqlite3
import os
from datetime import datetime
import csv
from io import StringIO
import secrets
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_change_in_production')

# Google OAuth Configuration (you'll need to set these environment variables)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'your-google-client-secret')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')

# ---------------- DATABASE CONNECTION ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "parking.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- DATABASE MIGRATION ----------------
def migrate_database():
    """Add payment_platform, upi_id, notifications table, and settings table if they don't exist"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if payment_platform column exists in vehicles
    cursor.execute("PRAGMA table_info(vehicles)")
    vehicle_columns = [column[1] for column in cursor.fetchall()]
    
    if 'payment_platform' not in vehicle_columns:
        try:
            cursor.execute("ALTER TABLE vehicles ADD COLUMN payment_platform TEXT DEFAULT 'Cash'")
            conn.commit()
            print("✅ Added payment_platform column to vehicles table")
        except sqlite3.OperationalError as e:
            print(f"⚠️ Error adding column: {e}")
    
    # Check if upi_id column exists in users
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [column[1] for column in cursor.fetchall()]
    
    if 'upi_id' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN upi_id TEXT")
            conn.commit()
            print("✅ Added upi_id column to users table")
        except sqlite3.OperationalError as e:
            print(f"⚠️ Error adding column: {e}")
    
    # Create notifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    conn.commit()
    print("✅ Notifications table ready")
    
    # Create settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_slots INTEGER DEFAULT 50,
            hourly_rate INTEGER DEFAULT 20,
            notify_entry INTEGER DEFAULT 1,
            notify_exit INTEGER DEFAULT 1,
            notify_payment INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    conn.commit()
    print("✅ Settings table ready")
    
    conn.close()

# Run migration on startup
migrate_database()


# ---------------- NOTIFICATION HELPER ----------------
def add_notification(user_id, notification_type, message):
    """Add a notification for a user"""
    conn = get_db()
    conn.execute(
        "INSERT INTO notifications (user_id, type, message) VALUES (?, ?, ?)",
        (user_id, notification_type, message)
    )
    conn.commit()
    conn.close()


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


# ---------------- GOOGLE OAUTH ----------------
@app.route("/auth/google")
def google_auth():
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # Build Google OAuth URL
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        "response_type=code&"
        "scope=openid%20email%20profile&"
        f"state={state}"
    )
    
    return redirect(google_auth_url)


@app.route("/auth/google/callback")
def google_callback():
    # Verify state token
    state = request.args.get('state')
    if state != session.get('oauth_state'):
        return render_template("login.html", error="Invalid OAuth state")
    
    code = request.args.get('code')
    if not code:
        return render_template("login.html", error="OAuth authorization failed")
    
    try:
        # Exchange code for tokens
        import urllib.request
        import json
        
        token_data = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        token_request = urllib.request.Request(
            'https://oauth2.googleapis.com/token',
            data=json.dumps(token_data).encode(),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(token_request) as response:
            token_response = json.loads(response.read())
        
        access_token = token_response.get('access_token')
        
        # Get user info
        user_info_request = urllib.request.Request(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        with urllib.request.urlopen(user_info_request) as response:
            user_info = json.loads(response.read())
        
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        google_id = user_info.get('id')
        
        # Check if user exists
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        
        if user:
            # User exists, log them in
            session['user_id'] = user['user_id']
            session['username'] = user['username']
        else:
            # Create new user
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (name, email, f'google_oauth_{google_id}')
            )
            conn.commit()
            
            # Get the new user
            user = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()
            
            session['user_id'] = user['user_id']
            session['username'] = user['username']
        
        conn.close()
        
        return redirect(url_for("dashboard"))
        
    except Exception as e:
        print(f"OAuth error: {e}")
        return render_template("login.html", error="Failed to authenticate with Google")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- PROFILE ----------------
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (session['user_id'],)
    ).fetchone()
    conn.close()
    
    return render_template("profile.html", user=user)


# ---------------- SETTINGS ----------------
@app.route("/settings")
def settings():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    
    # Get settings (create default settings if not exists)
    settings_data = conn.execute("SELECT * FROM settings WHERE user_id = ?", (session['user_id'],)).fetchone()
    
    if not settings_data:
        # Create default settings
        conn.execute("""
            INSERT INTO settings (user_id, total_slots, hourly_rate, notify_entry, notify_exit, notify_payment)
            VALUES (?, 50, 20, 1, 1, 1)
        """, (session['user_id'],))
        conn.commit()
        settings_data = conn.execute("SELECT * FROM settings WHERE user_id = ?", (session['user_id'],)).fetchone()
    
    conn.close()
    
    # Get success/error messages from query params
    success_msg = request.args.get('success')
    error_msg = request.args.get('error')
    
    return render_template("settings.html", 
                         settings=dict(settings_data) if settings_data else {}, 
                         current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         success=success_msg,
                         error=error_msg)


# ---------------- UPDATE PARKING SETTINGS ----------------
@app.route("/settings/parking", methods=["POST"])
def update_parking_settings():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    total_slots = request.form.get("total_slots", 50)
    hourly_rate = request.form.get("hourly_rate", 20)
    
    conn = get_db()
    conn.execute("""
        UPDATE settings 
        SET total_slots = ?, hourly_rate = ?
        WHERE user_id = ?
    """, (total_slots, hourly_rate, session['user_id']))
    conn.commit()
    conn.close()
    
    return redirect(url_for("settings", success="Parking settings updated successfully"))


# ---------------- UPDATE NOTIFICATION SETTINGS ----------------
@app.route("/settings/notifications", methods=["POST"])
def update_notification_settings():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    notify_entry = 1 if request.form.get("notify_entry") else 0
    notify_exit = 1 if request.form.get("notify_exit") else 0
    notify_payment = 1 if request.form.get("notify_payment") else 0
    
    conn = get_db()
    conn.execute("""
        UPDATE settings 
        SET notify_entry = ?, notify_exit = ?, notify_payment = ?
        WHERE user_id = ?
    """, (notify_entry, notify_exit, notify_payment, session['user_id']))
    conn.commit()
    conn.close()
    
    return redirect(url_for("settings", success="Notification preferences updated"))


# ---------------- CLEAR ALL DATA ----------------
@app.route("/settings/clear-data")
def clear_data():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    
    # Delete all vehicles and reset parking slots
    conn.execute("DELETE FROM vehicles")
    conn.execute("UPDATE parking_slots SET status = 'Available'")
    conn.execute("DELETE FROM notifications WHERE user_id = ?", (session['user_id'],))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for("settings", success="All data cleared successfully"))


# ---------------- UPDATE PROFILE ----------------
@app.route("/profile/update", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    username = request.form.get("username")
    email = request.form.get("email")
    upi_id = request.form.get("upi_id", "").strip()
    old_password = request.form.get("old_password")
    new_password = request.form.get("password")
    
    conn = get_db()
    
    # Get current user data
    user = conn.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (session['user_id'],)
    ).fetchone()
    
    # Check if email is already taken by another user
    existing = conn.execute(
        "SELECT user_id FROM users WHERE email = ? AND user_id != ?",
        (email, session['user_id'])
    ).fetchone()
    
    if existing:
        conn.close()
        return render_template(
            "profile.html",
            user=user,
            error="Email already taken by another user"
        )
    
    # If password change is requested
    if old_password or new_password:
        # Both fields must be provided
        if not old_password or not new_password:
            conn.close()
            return render_template(
                "profile.html",
                user=user,
                error="Both current password and new password are required to change password"
            )
        
        # Verify old password
        if old_password != user['password']:
            conn.close()
            return render_template(
                "profile.html",
                user=user,
                error="Current password is incorrect"
            )
        
        # Update with new password and UPI ID
        conn.execute(
            "UPDATE users SET username = ?, email = ?, password = ?, upi_id = ? WHERE user_id = ?",
            (username, email, new_password, upi_id, session['user_id'])
        )
    else:
        # Update without password change, but with UPI ID
        conn.execute(
            "UPDATE users SET username = ?, email = ?, upi_id = ? WHERE user_id = ?",
            (username, email, upi_id, session['user_id'])
        )
    
    conn.commit()
    conn.close()
    
    # Update session
    session['username'] = username
    
    return redirect(url_for("dashboard"))


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    
    # Get user details
    user = conn.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (session['user_id'],)
    ).fetchone()

    # Total amount collected
    cur.execute("SELECT SUM(fee) FROM vehicles WHERE fee IS NOT NULL")
    total_amount = cur.fetchone()[0] or 0

    # Parking slots
    cur.execute("SELECT * FROM parking_slots")
    slots = cur.fetchall()

    # Vehicle records
    cur.execute("SELECT * FROM vehicles")
    vehicles = cur.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        username=session.get("username"),
        user_email=user['email'],
        slots=slots,
        vehicles=vehicles,
        total_amount=total_amount
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
        
        # Add notification
        add_notification(
            session['user_id'],
            'vehicle_entry',
            f"Vehicle {vehicle_no} entered at slot {slot_id}"
        )

        return redirect(url_for("dashboard"))

    return render_template("vehicle_entry.html")


# ---------------- CALCULATE FEE (AJAX) ----------------
@app.route("/calculate-fee", methods=["POST"])
def calculate_fee():
    if "user_id" not in session:
        return {"error": "Unauthorized"}, 401
    
    data = request.get_json()
    vehicle_no = data.get("vehicle_no")
    
    if not vehicle_no:
        return {"error": "Vehicle number required"}, 400
    
    conn = get_db()
    vehicle = conn.execute("""
        SELECT v.vehicle_id, v.entry_time, v.slot_id, s.slot_name
        FROM vehicles v
        JOIN parking_slots s ON v.slot_id = s.slot_id
        WHERE v.vehicle_no = ? AND v.exit_time IS NULL
    """, (vehicle_no,)).fetchone()
    
    if vehicle is None:
        conn.close()
        return {"error": "Vehicle not found or already exited"}, 404
    
    # Get user's UPI ID
    user = conn.execute(
        "SELECT upi_id FROM users WHERE user_id = ?",
        (session['user_id'],)
    ).fetchone()
    
    # Fee calculation (₹20 per hour)
    entry = datetime.strptime(vehicle["entry_time"], "%Y-%m-%d %H:%M:%S")
    exit_ = datetime.now()
    hours = max(1, int((exit_ - entry).total_seconds() // 3600 + 1))
    fee = hours * 20
    
    conn.close()
    
    return {
        "fee": fee,
        "slot_name": vehicle["slot_name"],
        "hours": hours,
        "upi_id": user['upi_id'] if user and user['upi_id'] else None
    }


# ---------------- VEHICLE EXIT ----------------
@app.route("/vehicle-exit", methods=["GET", "POST"])
def vehicle_exit():
    if request.method == "POST":
        vehicle_no = request.form["vehicle_no"]
        payment_platform = request.form.get("payment_platform", "Cash")
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

        # Update vehicle with payment platform
        conn.execute("""
            UPDATE vehicles
            SET exit_time = ?, fee = ?, payment_platform = ?
            WHERE vehicle_id = ?
        """, (exit_time, fee, payment_platform, vehicle["vehicle_id"]))

        # Free slot
        conn.execute("""
            UPDATE parking_slots
            SET status = 'Available'
            WHERE slot_id = ?
        """, (vehicle["slot_id"],))

        conn.commit()
        conn.close()
        
        # Add notifications
        add_notification(
            session['user_id'],
            'vehicle_exit',
            f"Vehicle {vehicle_no} exited from slot {vehicle['slot_name']}"
        )
        
        add_notification(
            session['user_id'],
            'payment_completed',
            f"Payment of ₹{fee} received for {vehicle_no} via {payment_platform}"
        )

        # Redirect to vehicle exit page with success message via query params
        return redirect(url_for('vehicle_exit', 
                               success='true', 
                               vehicle_no=vehicle_no,
                               slot_name=vehicle["slot_name"],
                               fee=fee,
                               payment_platform=payment_platform))

    # Handle GET request with success parameters
    success = request.args.get('success') == 'true'
    vehicle_no = request.args.get('vehicle_no')
    slot_name = request.args.get('slot_name')
    fee = request.args.get('fee')
    payment_platform = request.args.get('payment_platform')
    
    # If no parameters, render empty form
    return render_template(
        "vehicle_exit.html",
        success=success if success else False,
        vehicle_no=vehicle_no if vehicle_no else None,
        slot_name=slot_name if slot_name else None,
        fee=fee if fee else None,
        payment_platform=payment_platform if payment_platform else None
    )


@app.route("/payments")
def payments():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    # Get all completed payments with details
    cur.execute("""
        SELECT v.vehicle_no, v.owner_name, v.entry_time, v.exit_time, 
               v.fee, v.payment_platform, s.slot_name
        FROM vehicles v
        JOIN parking_slots s ON v.slot_id = s.slot_id
        WHERE v.fee IS NOT NULL
        ORDER BY v.exit_time DESC
    """)
    payment_records = cur.fetchall()

    # Amount collected till now
    cur.execute("SELECT SUM(fee) FROM vehicles WHERE fee IS NOT NULL")
    collected = cur.fetchone()[0] or 0

    # Payment platform breakdown
    cur.execute("""
        SELECT payment_platform, SUM(fee) as total, COUNT(*) as count
        FROM vehicles
        WHERE fee IS NOT NULL AND payment_platform IS NOT NULL
        GROUP BY payment_platform
    """)
    platform_stats = cur.fetchall()

    # Vehicles still parked (amount to be collected)
    cur.execute("""
        SELECT entry_time FROM vehicles
        WHERE exit_time IS NULL
    """)
    active_vehicles = cur.fetchall()

    to_be_collected = 0
    now = datetime.now()

    for v in active_vehicles:
        entry = datetime.strptime(v["entry_time"], "%Y-%m-%d %H:%M:%S")
        hours = max(1, int((now - entry).total_seconds() // 3600 + 1))
        to_be_collected += hours * 20

    total_amount = collected + to_be_collected

    conn.close()

    return render_template(
        "payments.html",
        collected=collected,
        to_be_collected=to_be_collected,
        total_amount=total_amount,
        payment_records=payment_records,
        platform_stats=platform_stats
    )


# ---------------- EXPORT DATA ----------------
@app.route("/export")
def export_data():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    cur = conn.cursor()
    
    # Create CSV output
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['VEHICLE PARKING MANAGEMENT SYSTEM - EXPORT REPORT'])
    writer.writerow(['Generated on:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow([])
    
    # PARKING SLOTS SUMMARY
    writer.writerow(['=== PARKING SLOTS SUMMARY ==='])
    cur.execute("SELECT * FROM parking_slots")
    slots = cur.fetchall()
    total_slots = len(slots)
    occupied = len([s for s in slots if s['status'] == 'Occupied'])
    available = len([s for s in slots if s['status'] == 'Available'])
    
    writer.writerow(['Total Slots:', total_slots])
    writer.writerow(['Occupied Slots:', occupied])
    writer.writerow(['Available Slots:', available])
    writer.writerow(['Occupancy Rate:', f'{(occupied/total_slots*100):.1f}%' if total_slots > 0 else '0%'])
    writer.writerow([])
    
    # PARKING SLOTS DETAILS
    writer.writerow(['=== PARKING SLOTS DETAILS ==='])
    writer.writerow(['Slot ID', 'Status', 'Vehicle Number (if occupied)'])
    cur.execute("""
        SELECT ps.slot_id, ps.status, 
               CASE WHEN v.vehicle_no IS NOT NULL THEN v.vehicle_no ELSE '-' END as vehicle
        FROM parking_slots ps
        LEFT JOIN vehicles v ON ps.slot_id = v.slot_id AND v.exit_time IS NULL
        ORDER BY ps.slot_id
    """)
    for row in cur.fetchall():
        writer.writerow([row['slot_id'], row['status'], row['vehicle']])
    writer.writerow([])
    
    # VEHICLE RECORDS
    writer.writerow(['=== VEHICLE PARKING RECORDS ==='])
    writer.writerow(['Vehicle Number', 'Owner Name', 'Slot ID', 'Entry Time', 'Exit Time', 'Fee (₹)', 'Payment Platform'])
    cur.execute("""
        SELECT vehicle_no, owner_name, slot_id, entry_time, exit_time, 
               COALESCE(fee, 0) as fee, COALESCE(payment_platform, 'Cash') as platform
        FROM vehicles 
        ORDER BY entry_time DESC
    """)
    vehicles = cur.fetchall()
    for v in vehicles:
        writer.writerow([
            v['vehicle_no'],
            v['owner_name'],
            v['slot_id'],
            v['entry_time'],
            v['exit_time'] if v['exit_time'] else 'Still Parked',
            f"₹{v['fee']}" if v['fee'] else 'Pending',
            v['platform']
        ])
    writer.writerow([])
    
    # PAYMENT SUMMARY
    writer.writerow(['=== PAYMENT SUMMARY ==='])
    cur.execute("SELECT SUM(fee) FROM vehicles WHERE fee IS NOT NULL")
    total_collected = cur.fetchone()[0] or 0
    
    cur.execute("SELECT COUNT(*) FROM vehicles WHERE exit_time IS NULL")
    pending_vehicles = cur.fetchone()[0] or 0
    
    # Calculate pending amount
    cur.execute("""
        SELECT entry_time FROM vehicles 
        WHERE exit_time IS NULL AND entry_time IS NOT NULL
    """)
    pending_amount = 0
    for row in cur.fetchall():
        entry = datetime.strptime(row['entry_time'], "%Y-%m-%d %H:%M:%S")
        hours = max(1, int((datetime.now() - entry).total_seconds() // 3600 + 1))
        pending_amount += hours * 20
    
    writer.writerow(['Total Revenue Collected:', f'₹{total_collected}'])
    writer.writerow(['Pending Revenue:', f'₹{pending_amount}'])
    writer.writerow(['Total Expected Revenue:', f'₹{total_collected + pending_amount}'])
    writer.writerow(['Vehicles Currently Parked:', pending_vehicles])
    writer.writerow([])
    
    # PAYMENT PLATFORM BREAKDOWN
    writer.writerow(['=== PAYMENT PLATFORM BREAKDOWN ==='])
    cur.execute("""
        SELECT COALESCE(payment_platform, 'Cash') as platform, 
               COUNT(*) as count, 
               SUM(fee) as total
        FROM vehicles 
        WHERE fee IS NOT NULL
        GROUP BY payment_platform
    """)
    writer.writerow(['Platform', 'Transactions', 'Total Amount (₹)'])
    for row in cur.fetchall():
        writer.writerow([row['platform'], row['count'], f"₹{row['total']}"])
    
    conn.close()
    
    # Create response with proper headers
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename="vpms_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


# ---------------- GET NOTIFICATIONS ----------------
@app.route("/api/notifications")
def get_notifications():
    if "user_id" not in session:
        return {"notifications": [], "unread_count": 0}
    
    conn = get_db()
    notifications = conn.execute("""
        SELECT id, type, message, is_read, created_at
        FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 10
    """, (session['user_id'],)).fetchall()
    
    unread_count = conn.execute("""
        SELECT COUNT(*) as count
        FROM notifications
        WHERE user_id = ? AND is_read = 0
    """, (session['user_id'],)).fetchone()['count']
    
    conn.close()
    
    return {
        "notifications": [dict(n) for n in notifications],
        "unread_count": unread_count
    }


# ---------------- MARK NOTIFICATION AS READ ----------------
@app.route("/api/notifications/<int:notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):
    if "user_id" not in session:
        return {"error": "Unauthorized"}, 401
    
    conn = get_db()
    conn.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE id = ? AND user_id = ?
    """, (notification_id, session['user_id']))
    conn.commit()
    conn.close()
    
    return {"success": True}


# ---------------- MARK ALL NOTIFICATIONS AS READ ----------------
@app.route("/api/notifications/read-all", methods=["POST"])
def mark_all_notifications_read():
    if "user_id" not in session:
        return {"error": "Unauthorized"}, 401
    
    conn = get_db()
    conn.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
    """, (session['user_id'],))
    conn.commit()
    conn.close()
    
    return {"success": True}


# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True, port=8000)
