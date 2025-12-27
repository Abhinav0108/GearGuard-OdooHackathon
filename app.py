import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Timezone Handling
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    IST = None 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hackathon-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gearguard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ================= MODELS =================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50))

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(100))
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    team = db.relationship('Team', backref='equipments')
    status = db.Column(db.String(50), default='Active')
    requests = db.relationship('MaintenanceRequest', backref='equipment', lazy=True)

class MaintenanceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    request_type = db.Column(db.String(50))
    status = db.Column(db.String(50), default='New')
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'))
    scheduled_date = db.Column(db.Date, nullable=True)
    technician_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    technician = db.relationship('User', backref='assigned_requests')
    
    # 🔥 Timestamps for Logic
    created_at = db.Column(db.DateTime, default=datetime.now)
    resolved_at = db.Column(db.DateTime, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ================= ROUTES =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    new_reqs = MaintenanceRequest.query.filter_by(status='New').all()
    progress_reqs = MaintenanceRequest.query.filter_by(status='In Progress').all()
    repaired_reqs = MaintenanceRequest.query.filter_by(status='Repaired').all()
    scrap_reqs = MaintenanceRequest.query.filter_by(status='Scrap').all()
    equipments = Equipment.query.all()
    technicians = User.query.all()
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('dashboard.html', 
                           new=new_reqs, 
                           progress=progress_reqs, 
                           repaired=repaired_reqs, 
                           scrap=scrap_reqs, 
                           equipments=equipments, 
                           technicians=technicians,
                           today_date=today_date, 
                           current_user=current_user)

@app.route('/create_request', methods=['POST'])
@login_required
def create_request():
    equipment_id = request.form.get('equipment_id')
    subject = request.form.get('subject')
    req_type = request.form.get('request_type')
    date_str = request.form.get('scheduled_date')
    tech_id = request.form.get('technician_id')
    
    scheduled_date = None
    if date_str:
        try: scheduled_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except: pass
        
    assigned_tech = int(tech_id) if tech_id else None
    
    new_request = MaintenanceRequest(
        subject=subject, request_type=req_type, equipment_id=equipment_id,
        status='New', scheduled_date=scheduled_date, technician_id=assigned_tech
    )
    db.session.add(new_request)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/assign_manual/<int:req_id>', methods=['POST'])
@login_required
def assign_manual(req_id):
    req = MaintenanceRequest.query.get_or_404(req_id)
    tech_id = request.form.get('technician_id')
    if tech_id:
        req.technician_id = int(tech_id)
        if req.status == 'New': req.status = 'In Progress'
        if not req.created_at: req.created_at = datetime.now()
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/move/<int:req_id>/<string:new_status>')
@login_required
def move_request(req_id, new_status):
    req = MaintenanceRequest.query.get_or_404(req_id)
    req.status = new_status
    
    # 🔥 Logic: Record Time when Repaired
    if new_status == 'Repaired' and req.resolved_at is None:
        req.resolved_at = datetime.now()
        
    if new_status == 'Scrap':
        equip = Equipment.query.get(req.equipment_id)
        equip.status = 'Scrapped'
        
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/archive/<int:req_id>')
@login_required
def archive_request(req_id):
    req = MaintenanceRequest.query.get_or_404(req_id)
    db.session.delete(req)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/equipment')
@login_required
def equipment_list():
    items = Equipment.query.all()
    return render_template('equipment.html', items=items)

@app.route('/equipment/<int:id>/requests')
@login_required
def equipment_requests(id):
    equip = Equipment.query.get_or_404(id)
    reqs = MaintenanceRequest.query.filter_by(equipment_id=id).all()
    return render_template('equipment_requests.html', equipment=equip, requests=reqs)

@app.route("/calendar")
@login_required
def calendar_page():
    return render_template("calendar.html")

@app.route("/calendar/events")
@login_required
def calendar_events():
    events = []
    requests = MaintenanceRequest.query.all()
    for r in requests:
        if r.status == "Scrap": continue
        event_date = r.scheduled_date or r.created_at.date()
        
        # Color Logic
        color = '#ffc107' # Yellow
        text_color = 'black'
        if r.status == 'In Progress':
            color = '#0d6efd' # Blue
            text_color = 'white'
        elif r.status == 'Repaired':
            color = '#198754' # Green
            text_color = 'white'

        events.append({
            "id": r.id,
            "title": f"{r.subject} ({r.technician.username if r.technician else 'Unassigned'})",
            "start": event_date.strftime("%Y-%m-%d"),
            "allDay": True,
            "color": color,
            "textColor": text_color,
            "url": f"/move/{r.id}/In Progress"
        })
    return jsonify(events)

def create_dummy_data():
    with app.app_context():
        db.create_all()
        # Create Users
        for name in ['admin', 'Alex_Tech', 'Bob_Mechanic', 'Charlie_IT']:
            if not User.query.filter_by(username=name).first():
                role = 'Manager' if name == 'admin' else 'Technician'
                db.session.add(User(username=name, password=generate_password_hash('1234'), role=role))
        
        # Create Teams
        for tname in ['Mechanics', 'IT Support', 'Production', 'Logistics']:
            if not Team.query.filter_by(name=tname).first():
                db.session.add(Team(name=tname))
        db.session.commit()
        
        # Create Equipment
        t_prod = Team.query.filter_by(name='Production').first()
        t_it = Team.query.filter_by(name='IT Support').first()
        t_log = Team.query.filter_by(name='Logistics').first()
        t_mech = Team.query.filter_by(name='Mechanics').first()

        equips = [
            ('CNC Machine 01', 'CNC-99', t_prod), ('Server Rack A', 'SRV-01', t_it),
            ('Hydraulic Press', 'HYD-500', t_prod), ('3D Printer Pro', '3DP-X1', t_it),
            ('Forklift Toyota', 'FL-99', t_log), ('Conveyor Belt A', 'CONV-A', t_mech),
            ('Welding Robot', 'WELD-R2', t_prod), ('Office WiFi Router', 'NET-05', t_it)
        ]
        for name, serial, team in equips:
            if not Equipment.query.filter_by(name=name).first():
                db.session.add(Equipment(name=name, serial_number=serial, team_id=team.id))
        
        db.session.commit()
        print("DB Initialized.")

if __name__ == '__main__':
    create_dummy_data()
    app.run(debug=True)
