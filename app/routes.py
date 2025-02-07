from flask import Blueprint, render_template, flash, redirect, request, url_for
from flask_login import login_user, login_required, logout_user, current_user
from psycopg2 import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from .forms import LoginForm, RegistrationForm, UserForm
from .models import User, db, Role, Appointment, Prescription, Payment, MedicalRecord, Doctor, Patient, Staff
from . import bcrypt 
from datetime import datetime
main_routes = Blueprint('main_routes', __name__)
admin_routes = Blueprint('admin', __name__)
patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

@patient_bp.route('/dashboard', methods=['GET'])
@login_required
def patient_dashboard():
    appointments = Appointment.query.filter_by(patient_id=current_user.id).all()
    return render_template('dashboard_patient.html', appointments=appointments)

from datetime import datetime

@patient_bp.route('/appointments/book', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        appointment_date_str = request.form['appointment_date']

        # Convert string to datetime object
        appointment_date = datetime.strptime(appointment_date_str, "%Y-%m-%dT%H:%M")

        new_appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_id,
            appointment_date=appointment_date
        )
        db.session.add(new_appointment)
        db.session.commit()

        return redirect(url_for('patient.patient_dashboard'))
    
    doctors = Doctor.query.all()  
    return render_template('book_appointment.html', doctors=doctors)


@patient_bp.route('/medical_records', methods=['GET'])
@login_required
def medical_records():
    records = MedicalRecord.query.filter_by(patient_id=current_user.id).all()
    return render_template('medical_records.html', records=records)

@admin_routes.route('/manage_users')
@login_required
def manage_users():
    print("Current User Role:", current_user.role.name)
    if current_user.role and current_user.role.name.lower() != 'admin':
        flash("You don't have permission to access this page.", 'danger')
        return redirect(url_for('main_routes.home'))
    
    users = User.query.all()  
    return render_template('manage_users.html', users=users)

@admin_routes.route('/add-user', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role.name.lower() != 'admin': 
        flash("You don't have permission to access this page.", 'danger')
        return redirect(url_for('main_routes.admin_dashboard'))

    form = UserForm()  

    if form.validate_on_submit():  
        username = form.username.data
        email = form.email.data
        password = form.password.data
        role_id = form.role.data  
        if not role_id:
            flash("Please select a role.", "danger")
            return render_template('add_user.html', form=form)

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists. Please choose a different one.", 'danger')
            return redirect(url_for('admin.add_user')) 

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8') 
        new_user = User(username=username, email=email, password=hashed_password, role_id=role_id)
        db.session.add(new_user)

        try:
            db.session.commit()
            flash('User added successfully!', 'success')
            return redirect(url_for('admin.manage_users'))  
        except IntegrityError:
            db.session.rollback()
            flash("Database error! This username or email already exists.", 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f"An unexpected error occurred: {str(e)}", 'danger')

    return render_template('add_user.html', form=form) 


@admin_routes.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role.name.lower() != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))

    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user) 
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.password = form.password.data
        user.role_id = form.role.data
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.manage_users'))

    return render_template('edit_user.html', form=form, user=user)

@admin_routes.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def delete_user(user_id):
    if current_user.role.name.lower() != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_routes.route('/manage_appointments')
@login_required
def manage_appointments():
    if current_user.role.name.lower() != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))

    appointments = Appointment.query.all()
    return render_template('manage_appointments.html', appointments=appointments)


@admin_routes.route('/manage_billing')
@login_required
def manage_billing():
    if current_user.role.name.lower() != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))

    payments = Payment.query.all()
    return render_template('manage_billing.html', payments=payments)

@main_routes.route('/admin/users')
@login_required
def view_users():
    if current_user.role == 'Admin':
        users = User.query.all()  
        return render_template('admin/view_users.html', users=users)
    else:
        flash("You don't have permission to view this page.", 'danger')

        if current_user.role == 'Admin':
            return redirect(url_for('admin.dashboard_admin'))
        elif current_user.role == 'Doctor':
            return redirect(url_for('doctor.dashboard_doctor'))
        elif current_user.role == 'Patient':
            return redirect(url_for('patient.dashboard_patient'))
        elif current_user.role == 'Staff':
            return redirect(url_for('staff.dashboard_staff'))
        else:
            return redirect(url_for('home'))  

    
@main_routes.route('/')
def home():
    return render_template('home.html')

@main_routes.route('/about')
def about():
    return render_template('about.html')

@main_routes.route('/contact')
def contact():
    return render_template('contact.html')

@main_routes.route('/role-selection')
def role_selection():
    return render_template('role_selection.html')

@main_routes.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if not user:
            flash('User does not exist. Please register first.', 'danger')
            return redirect(url_for('main_routes.register'))

        if user.role.name.lower() != role.lower():
            flash(f'Invalid role for {role}. Please log in with the correct role.', 'danger')
            return redirect(url_for('main_routes.login', role=role))

        if not bcrypt.check_password_hash(user.password, form.password.data):
            flash("Incorrect password. Please try again.", "danger")
            return redirect(url_for('main_routes.login', role=role))

        login_user(user, remember=True)
        flash("Login successful!", "success")
        if user.role.name.lower() == 'admin':
            return redirect(url_for('main_routes.admin_dashboard'))
        elif user.role.name.lower() == 'doctor':
            return redirect(url_for('main_routes.doctor_dashboard'))
        elif user.role.name.lower() == 'patient':
            return redirect(url_for('main_routes.patient_dashboard'))
        elif user.role.name.lower() == 'staff':
            return redirect(url_for('main_routes.staff_dashboard'))

    return render_template('login.html', role=role, form=form)


@main_routes.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    form.role.choices = [(role.id, role.name) for role in Role.query.all()]

    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already exists! Please use a different email.', 'danger')
            return render_template('register.html', form=form)
        
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        role = Role.query.get(form.role.data) 
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password, role=role)
        
        db.session.add(new_user)
        db.session.commit()
        
        if role.name.lower() == "doctor":
            new_doctor = Doctor(user_id=new_user.id, first_name=new_user.username, last_name="", email=new_user.email, specialization="General")
            db.session.add(new_doctor)
        elif role.name.lower() == "patient":
            new_patient = Patient(user_id=new_user.id, first_name=new_user.username, last_name="", date_of_birth=datetime.utcnow(), gender="Other", medical_history="None")
            db.session.add(new_patient)
        elif role.name.lower() == "staff":
            new_staff = Staff(user_id=new_user.id, position="Receptionist", contact_number="")
            db.session.add(new_staff)

        db.session.commit()

        flash('Your account has been created!', 'success')
        return redirect(url_for('main_routes.login', role=role.name)) 

    return render_template('register.html', form=form)

@main_routes.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out!', 'info')
    return redirect(url_for('main_routes.home'))


@main_routes.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role.name.lower() != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))
    
    return render_template('dashboard_admin.html')

@main_routes.route('/doctor_dashboard')
@login_required
def doctor_dashboard():
    if current_user.role.name.lower() != 'doctor':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))
    
    appointments = Appointment.query.filter_by(doctor_id=current_user.id).all()
    prescriptions = Prescription.query.filter_by(doctor_id=current_user.id).all()
    patients = [appt.patient for appt in appointments]

    return render_template('dashboard_doctor.html', appointments=appointments, prescriptions=prescriptions, patients=patients)

@main_routes.route('/patient_dashboard')
@login_required
def patient_dashboard():
    if current_user.role.name.lower() != 'patient':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))

    appointments = Appointment.query.filter_by(patient_id=current_user.id).all()

    return render_template('dashboard_patient.html', appointments=appointments)

@main_routes.route('/staff_dashboard')
@login_required
def staff_dashboard():
    if current_user.role.name.lower() != 'staff':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))

    return render_template('dashboard_staff.html')