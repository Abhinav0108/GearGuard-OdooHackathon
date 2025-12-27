
# GearGuard Maintenance Management System

A modern, web-based maintenance management system built with Flask. This application helps track equipment status, manage maintenance requests, schedule preventive maintenance, and analyze repair history.

##  Project File Structure

GearGuard/
│
├── instance/
│   └── gearguard.db            # SQLite database file storing Users, Teams, Equipment, and Requests
│
├── templates/                  # HTML templates for the frontend
│   ├── base.html               # Main layout file (Navbar, CSS links, Scripts) extended by other pages
│   ├── calendar.html           # Calendar view for scheduling preventive maintenance
│   ├── dashboard.html          # Main Kanban board for tracking request status (New, In Progress, Repaired)
│   ├── equipment.html          # Database view listing all assets and their status
│   ├── equipment_requests.html # History log showing all requests for a specific piece of equipment
│   └── login.html              # User authentication page
│
├── app.py                      # Main application entry point (Routes, Database Models, Logic)
│
└── requirements.txt            # List of Python dependencies (Flask, SQLAlchemy, etc.)


How to Run

1. Install Dependencies:

pip install -r requirements.txt



2. Initialize Database (Optional but Recommended):
Delete the existing `instance/gearguard.db` file to ensure a clean slate with the latest schema and dummy data.
3. Start the Server:

python app.py




4. Access the App:
Open your browser and navigate to `http://127.0.0.1:5000`.
* Login: `admin`
* Password: `admin123`

