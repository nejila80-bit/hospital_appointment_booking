# Hospital Appointment Booking System

A college-project full-stack web app based on the supplied abstract. It uses **Python + Flask**, **SQLite**, server-rendered HTML/CSS, and role-based sessions. It is designed to run in VS Code and includes a Git/GitHub practice workflow.

> **Important:** This is an educational demo, not a production medical system. Use only fictional data. Before any real deployment, add CSRF protection, secret management, audit logging, rate limiting, backups, privacy/security review, and appropriate healthcare compliance controls.

## Features

- Patient registration and sign-in with hashed passwords
- Separate patient, doctor, and admin dashboards
- Search doctors by name/specialization and filter by department
- View available appointment slots and book a slot
- Conditional slot updates to reduce double-booking conflicts
- Patient cancellation and appointment status tracking
- Doctor can add availability and manage their appointments
- Admin dashboard with summary statistics, recent appointments, doctor creation, user listing/deletion
- SQLite database created automatically with demo records
- Responsive layout for desktop and mobile
- `/health` endpoint for a basic app health check

## Requirements

- Python 3.10 or newer
- Visual Studio Code
- VS Code Python extension (recommended)
- Git installed

## Run in VS Code

1. Extract this folder and open `hospital_appointment_booking` in VS Code.
2. Open **Terminal → New Terminal**.
3. Create a virtual environment:

   **Windows PowerShell**
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **Windows Command Prompt**
   ```bat
   py -m venv .venv
   .venv\Scripts\activate.bat
   ```

   **macOS/Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
5. Start the app:
   ```bash
   python app.py
   ```
6. Open the local address printed in the terminal (normally `http://127.0.0.1:5000`).

The SQLite database (`hospital.db`) is created automatically on first run. Stop the server with `Ctrl+C`.

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Admin | `admin@hospital.demo` | `Admin123!` |
| Doctor | `maya@hospital.demo` | `Doctor123!` |
| Doctor | `arjun@hospital.demo` | `Doctor123!` |
| Doctor | `sara@hospital.demo` | `Doctor123!` |
| Patient | `patient@hospital.demo` | `Patient123!` |

You can also register a new patient account. Demo accounts are seeded only when the database is empty.

## Basic Git commands for your project

Run these commands in the VS Code terminal from the project folder:

```bash
git init
git status
git add .
git commit -m "Initial hospital appointment booking app"
git branch -M main
```

Create an empty repository on GitHub, then connect it (replace the URL with your repository URL):

```bash
git remote add origin https://github.com/YOUR-USERNAME/hospital-appointment-booking.git
git push -u origin main
```

For normal changes:

```bash
git status
git add .
git commit -m "Add doctor availability management"
git push
```

Useful commands:

```bash
git log --oneline
git diff
git branch
git pull
```

**Before committing:** check `git status`; make sure `.venv/`, `.env`, and `hospital.db` are not staged. `.gitignore` excludes them.

## Suggested college project demonstration

1. Sign in as a patient and search for a doctor.
2. Open the doctor's available slots, enter a reason, and book an appointment.
3. Sign in as that doctor in another browser/incognito window and confirm or complete the appointment.
4. Add a future availability slot as the doctor.
5. Sign in as admin to review dashboard counts, create a doctor, and inspect user accounts.
6. Show `git status`, `git log --oneline`, and a commit in the VS Code terminal.

## Project structure

```text
hospital_appointment_booking/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── patient_dashboard.html
│   ├── doctor_dashboard.html
│   ├── admin_dashboard.html
│   ├── doctors.html
│   ├── slots.html
│   └── admin_users.html
└── static/
    └── style.css
```
