import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hackathon-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gearguard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- MODELS ---

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

# --- LOGIN LOGIC ---

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

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
            flash('Login failed. Check credentials.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- MAIN WORKFLOWS ---

@app.route('/')
@login_required
def dashboard():
    # Fetch requests by status for Kanban columns
    new_reqs = MaintenanceRequest.query.filter_by(status='New').all()
    progress_reqs = MaintenanceRequest.query.filter_by(status='In Progress').all()
    repaired_reqs = MaintenanceRequest.query.filter_by(status='Repaired').all()
    scrap_reqs = MaintenanceRequest.query.filter_by(status='Scrap').all()
    
    # Fetch equipment for the dropdown in the "Create Request" modal
    equipments = Equipment.query.filter_by(status='Active').all()
    
    return render_template('dashboard.html', 
                         new=new_reqs, 
                         progress=progress_reqs, 
                         repaired=repaired_reqs, 
                         scrap=scrap_reqs,
                         equipments=equipments)

# THIS IS THE MISSING FUNCTION THAT CAUSED YOUR ERROR
@app.route('/create_request', methods=['POST'])
@login_required
def create_request():
    subject = request.form.get('subject')
    equip_id = request.form.get('equipment_id')
    req_type = request.form.get('request_type')
    
    new_req = MaintenanceRequest(
        subject=subject,
        request_type=req_type,
        equipment_id=equip_id,
        status='New',
        technician_id=current_user.id 
    )
    
    db.session.add(new_req)
    db.session.commit()
    flash('New maintenance request created!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/move/<int:req_id>/<string:new_status>')
@login_required
def move_request(req_id, new_status):
    req = MaintenanceRequest.query.get_or_404(req_id)
    req.status = new_status
    
    # Scrap Logic
    if new_status == 'Scrap':
        equip = Equipment.query.get(req.equipment_id)
        equip.status = 'Scrapped / Unusable'
        flash(f'Equipment {equip.name} marked as Scrapped.', 'warning')

    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/equipment')
@login_required
def equipment_list():
    items = Equipment.query.all()
    return render_template('equipment.html', items=items)

# --- SETUP SCRIPT ---
def create_dummy_data():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            # Create Default Admin
            admin = User(username='admin', password=generate_password_hash('admin123'), role='Manager')
            db.session.add(admin)
            
            # Create Teams
            t1 = Team(name='Mechanics')
            t2 = Team(name='IT Support')
            db.session.add_all([t1, t2])
            db.session.commit()

            # Create Equipment
            e1 = Equipment(name='CNC Machine 01', serial_number='CNC-99', team_id=t1.id)
            e2 = Equipment(name='Server Rack A', serial_number='SRV-01', team_id=t2.id)
            db.session.add_all([e1, e2])
            db.session.commit()
            print("Database initialized.")

if __name__ == '__main__':
    create_dummy_data()
    app.run(debug=True)