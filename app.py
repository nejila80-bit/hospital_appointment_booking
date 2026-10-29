import os
import sqlite3
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "hospital.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-secret")

DEPARTMENTS = ["Cardiology", "Dermatology", "General Medicine", "Neurology", "Orthopedics", "Pediatrics"]

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('patient','doctor','admin')),
      department TEXT, specialization TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS availability (
      id INTEGER PRIMARY KEY AUTOINCREMENT, doctor_id INTEGER NOT NULL,
      slot_date TEXT NOT NULL, slot_time TEXT NOT NULL, is_booked INTEGER NOT NULL DEFAULT 0,
      UNIQUE(doctor_id, slot_date, slot_time),
      FOREIGN KEY(doctor_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS appointments (
      id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL, doctor_id INTEGER NOT NULL,
      slot_id INTEGER, appointment_date TEXT NOT NULL, appointment_time TEXT NOT NULL,
      reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending'
        CHECK(status IN ('Pending','Confirmed','Completed','Cancelled')),
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(patient_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY(doctor_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY(slot_id) REFERENCES availability(id) ON DELETE SET NULL
    );
    """)
    # Demo accounts are created only when the users table is empty.
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        demo_users = [
          ("Admin User", "admin@hospital.demo", "Admin123!", "admin", None, None),
          ("Dr. Maya Nair", "maya@hospital.demo", "Doctor123!", "doctor", "Cardiology", "Cardiologist"),
          ("Dr. Arjun Menon", "arjun@hospital.demo", "Doctor123!", "doctor", "General Medicine", "General Physician"),
          ("Dr. Sara Thomas", "sara@hospital.demo", "Doctor123!", "doctor", "Pediatrics", "Pediatrician"),
          ("Demo Patient", "patient@hospital.demo", "Patient123!", "patient", None, None),
        ]
        for name, email, password, role, department, specialization in demo_users:
            db.execute("INSERT INTO users(name,email,password_hash,role,department,specialization) VALUES(?,?,?,?,?,?)",
                       (name, email, generate_password_hash(password), role, department, specialization))
        doctors = db.execute("SELECT id FROM users WHERE role='doctor'").fetchall()
        from datetime import timedelta
        for doctor in doctors:
            for day_offset in range(1, 8):
                day = (date.today() + timedelta(days=day_offset)).isoformat()
                for time in ("09:00", "10:00", "11:00", "14:00", "15:00"):
                    db.execute("INSERT OR IGNORE INTO availability(doctor_id,slot_date,slot_time) VALUES(?,?,?)",
                               (doctor["id"], day, time))
        db.commit()
    db.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You do not have permission to access that page.", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@app.context_processor
def inject_user():
    return {"current_user": dict(session) if session.get("user_id") else None,
            "today": date.today().isoformat()}

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    db = get_db()
    doctor_count = db.execute("SELECT COUNT(*) FROM users WHERE role='doctor'").fetchone()[0]
    return render_template("index.html", doctor_count=doctor_count)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name and email, and use a password with at least 8 characters.", "error")
            return render_template("register.html")
        try:
            get_db().execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'patient')",
                             (name, email, generate_password_hash(password)))
            get_db().commit()
            flash("Account created. You can now sign in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "error")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["id"], name=user["name"], email=user["email"], role=user["role"])
            flash(f"Welcome back, {user['name'].split()[0]}!", "success")
            return redirect(url_for("dashboard"))
        flash("Email or password was incorrect.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    role = session["role"]
    if role == "patient":
        appointments = db.execute("""
          SELECT a.*, d.name AS doctor_name, d.department FROM appointments a
          JOIN users d ON d.id=a.doctor_id WHERE a.patient_id=?
          ORDER BY a.appointment_date DESC, a.appointment_time DESC""", (session["user_id"],)).fetchall()
        return render_template("patient_dashboard.html", appointments=appointments)
    if role == "doctor":
        appointments = db.execute("""
          SELECT a.*, p.name AS patient_name FROM appointments a
          JOIN users p ON p.id=a.patient_id WHERE a.doctor_id=?
          ORDER BY a.appointment_date, a.appointment_time""", (session["user_id"],)).fetchall()
        slots = db.execute("SELECT * FROM availability WHERE doctor_id=? AND slot_date>=? ORDER BY slot_date,slot_time",
                           (session["user_id"], date.today().isoformat())).fetchall()
        return render_template("doctor_dashboard.html", appointments=appointments, slots=slots)
    stats = {
      "patients": db.execute("SELECT COUNT(*) FROM users WHERE role='patient'").fetchone()[0],
      "doctors": db.execute("SELECT COUNT(*) FROM users WHERE role='doctor'").fetchone()[0],
      "appointments": db.execute("SELECT COUNT(*) FROM appointments").fetchone()[0],
      "pending": db.execute("SELECT COUNT(*) FROM appointments WHERE status='Pending'").fetchone()[0],
    }
    appointments = db.execute("""
      SELECT a.*, p.name AS patient_name, d.name AS doctor_name FROM appointments a
      JOIN users p ON p.id=a.patient_id JOIN users d ON d.id=a.doctor_id
      ORDER BY a.created_at DESC LIMIT 10""").fetchall()
    doctors = db.execute("SELECT * FROM users WHERE role='doctor' ORDER BY name").fetchall()
    return render_template("admin_dashboard.html", stats=stats, appointments=appointments, doctors=doctors)

@app.route("/doctors")
@login_required
def doctors():
    db = get_db()
    query = request.args.get("q", "").strip()
    department = request.args.get("department", "").strip()
    sql = "SELECT * FROM users WHERE role='doctor'"
    params = []
    if query:
        sql += " AND (name LIKE ? OR specialization LIKE ?)"
        params += [f"%{query}%", f"%{query}%"]
    if department:
        sql += " AND department=?"
        params.append(department)
    sql += " ORDER BY name"
    rows = db.execute(sql, params).fetchall()
    return render_template("doctors.html", doctors=rows, departments=DEPARTMENTS, query=query, selected_department=department)

@app.route("/doctors/<int:doctor_id>/slots")
@login_required
def doctor_slots(doctor_id):
    db = get_db()
    doctor = db.execute("SELECT * FROM users WHERE id=? AND role='doctor'", (doctor_id,)).fetchone()
    if not doctor:
        flash("Doctor not found.", "error")
        return redirect(url_for("doctors"))
    slots = db.execute("""SELECT * FROM availability WHERE doctor_id=? AND is_booked=0 AND slot_date>=?
                          ORDER BY slot_date,slot_time""", (doctor_id, date.today().isoformat())).fetchall()
    return render_template("slots.html", doctor=doctor, slots=slots)

@app.route("/appointments/book", methods=["POST"])
@login_required
@role_required("patient")
def book_appointment():
    db = get_db()
    slot_id = request.form.get("slot_id", type=int)
    reason = request.form.get("reason", "").strip()
    slot = db.execute("""SELECT * FROM availability WHERE id=? AND is_booked=0 AND slot_date>=?""",
                      (slot_id, date.today().isoformat())).fetchone() if slot_id else None
    if not slot or not reason:
        flash("That slot is no longer available, or the reason is missing. Please try again.", "error")
        return redirect(request.referrer or url_for("doctors"))
    try:
        # Conditional update prevents two patients from claiming the same slot.
        changed = db.execute("UPDATE availability SET is_booked=1 WHERE id=? AND is_booked=0", (slot_id,)).rowcount
        if changed != 1:
            db.rollback()
            flash("Sorry, that slot was just booked. Choose another time.", "error")
            return redirect(url_for("doctor_slots", doctor_id=slot["doctor_id"]))
        db.execute("""INSERT INTO appointments(patient_id,doctor_id,slot_id,appointment_date,appointment_time,reason)
                      VALUES(?,?,?,?,?,?)""",
                   (session["user_id"], slot["doctor_id"], slot_id, slot["slot_date"], slot["slot_time"], reason))
        db.commit()
        flash("Appointment request submitted successfully.", "success")
    except sqlite3.Error:
        db.rollback()
        flash("Could not book this appointment. Please try again.", "error")
    return redirect(url_for("dashboard"))

@app.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
@login_required
def cancel_appointment(appointment_id):
    db = get_db()
    appointment = db.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
    if not appointment:
        flash("Appointment not found.", "error")
    elif session["role"] == "patient" and appointment["patient_id"] != session["user_id"]:
        flash("You cannot cancel another patient's appointment.", "error")
    elif session["role"] == "doctor" and appointment["doctor_id"] != session["user_id"]:
        flash("You cannot update another doctor's appointment.", "error")
    elif session["role"] == "admin" or session["role"] == "patient" or session["role"] == "doctor":
        if appointment["status"] in ("Cancelled", "Completed"):
            flash("This appointment can no longer be cancelled.", "warning")
        else:
            db.execute("UPDATE appointments SET status='Cancelled' WHERE id=?", (appointment_id,))
            if appointment["slot_id"]:
                db.execute("UPDATE availability SET is_booked=0 WHERE id=?", (appointment["slot_id"],))
            db.commit()
            flash("Appointment cancelled.", "success")
    return redirect(url_for("dashboard"))

@app.route("/appointments/<int:appointment_id>/status", methods=["POST"])
@login_required
@role_required("doctor", "admin")
def update_appointment_status(appointment_id):
    status = request.form.get("status", "")
    if status not in ("Pending", "Confirmed", "Completed", "Cancelled"):
        flash("Invalid status.", "error")
        return redirect(url_for("dashboard"))
    db = get_db()
    appointment = db.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
    if not appointment or (session["role"] == "doctor" and appointment["doctor_id"] != session["user_id"]):
        flash("Appointment not found or access denied.", "error")
    else:
        old_status = appointment["status"]
        db.execute("UPDATE appointments SET status=? WHERE id=?", (status, appointment_id))
        if status == "Cancelled" and appointment["slot_id"]:
            db.execute("UPDATE availability SET is_booked=0 WHERE id=?", (appointment["slot_id"],))
        elif old_status == "Cancelled" and status != "Cancelled" and appointment["slot_id"]:
            db.execute("UPDATE availability SET is_booked=1 WHERE id=?", (appointment["slot_id"],))
        db.commit()
        flash("Appointment status updated.", "success")
    return redirect(url_for("dashboard"))

@app.route("/availability/add", methods=["POST"])
@login_required
@role_required("doctor")
def add_availability():
    slot_date = request.form.get("slot_date", "")
    slot_time = request.form.get("slot_time", "")
    if not slot_date or not slot_time or slot_date < date.today().isoformat():
        flash("Choose a valid future date and time.", "error")
        return redirect(url_for("dashboard"))
    try:
        get_db().execute("INSERT INTO availability(doctor_id,slot_date,slot_time) VALUES(?,?,?)",
                         (session["user_id"], slot_date, slot_time))
        get_db().commit()
        flash("Availability added.", "success")
    except sqlite3.IntegrityError:
        flash("That availability slot already exists.", "error")
    return redirect(url_for("dashboard"))

@app.route("/admin/doctors/add", methods=["POST"])
@login_required
@role_required("admin")
def add_doctor():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    department = request.form.get("department", "")
    specialization = request.form.get("specialization", "").strip()
    if not name or not email or len(password) < 8 or department not in DEPARTMENTS or not specialization:
        flash("Fill in all doctor fields. Password must be at least 8 characters.", "error")
        return redirect(url_for("dashboard"))
    try:
        get_db().execute("""INSERT INTO users(name,email,password_hash,role,department,specialization)
                            VALUES(?,?,?,'doctor',?,?)""",
                         (name, email, generate_password_hash(password), department, specialization))
        get_db().commit()
        flash("Doctor account created.", "success")
    except sqlite3.IntegrityError:
        flash("That email is already registered.", "error")
    return redirect(url_for("dashboard"))

@app.route("/admin/users")
@login_required
@role_required("admin")
def admin_users():
    users = get_db().execute("SELECT id,name,email,role,department,specialization,created_at FROM users ORDER BY role,name").fetchall()
    return render_template("admin_users.html", users=users)

@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_user(user_id):
    if user_id == session["user_id"]:
        flash("You cannot delete the account you are currently using.", "error")
        return redirect(url_for("admin_users"))
    user = get_db().execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        flash("User not found.", "error")
    else:
        get_db().execute("DELETE FROM users WHERE id=?", (user_id,))
        get_db().commit()
        flash("User deleted.", "success")
    return redirect(url_for("admin_users"))

@app.route("/health")
def health():
    return {"status": "ok", "app": "Hospital Appointment Booking System"}

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
