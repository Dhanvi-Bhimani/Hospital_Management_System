from flask import Blueprint, render_template, flash, redirect, request, url_for, Response
from flask_login import login_user, login_required, logout_user, current_user
from psycopg2 import IntegrityError
from .forms import LoginForm, RegistrationForm, UserForm
from .models import User, db, Role, Appointment, Prescription, Payment, MedicalRecord, Doctor, Patient, Staff, Pharmacy
from . import bcrypt 
import uuid
import csv, io
from datetime import datetime
main_routes = Blueprint('main_routes', __name__)
admin_routes = Blueprint('admin', __name__)
patient_bp = Blueprint('patient', __name__, url_prefix='/patient')
doctor_routes = Blueprint('doctor_routes', __name__)
staff_bp = Blueprint("staff", __name__, url_prefix="/staff")
pharmacy = Blueprint('pharmacy', __name__)

@pharmacy.route('/inventory')
def view_inventory():
    # Query the database for all medicines (from the Pharmacy table)
    medicines = Pharmacy.query.all()
    return render_template('view_inventory.html', medicines=medicines)

@pharmacy.route('/view_medicine/<int:medicine_id>', methods=['GET'])
def view_medicine(medicine_id):
    # Logic to fetch and display the medicine details using medicine_id
    medicine = Pharmacy.query.get(medicine_id)
    return render_template('view_medicine.html', medicine=medicine)

@pharmacy.route('/edit_medicine/<int:medicine_id>', methods=['GET', 'POST'])
def edit_medicine(medicine_id):
    # Logic to fetch and edit medicine details using medicine_id
    medicine = Pharmacy.query.get(medicine_id)
    if request.method == 'POST':
        # Process form submission and update the medicine
        medicine.name = request.form['name']
        medicine.stock_quantity = request.form['stock_quantity']
        db.session.commit()
        return redirect(url_for('pharmacy.view_inventory'))
    return render_template('edit_medicine.html', medicine=medicine)

@pharmacy.route('/delete_medicine/<int:medicine_id>', methods=['POST'])
def delete_medicine(medicine_id):
    # Logic to delete medicine by id
    medicine = Pharmacy.query.get(medicine_id)
    if medicine:
        db.session.delete(medicine)
        db.session.commit()
    return redirect(url_for('pharmacy.view_inventory'))


@pharmacy.route('/add_medicine', methods=['GET', 'POST'])
def add_medicine():
    if request.method == 'POST':
        medicine_name = request.form.get('medicine_name')
        stock_quantity = request.form.get('stock_quantity')
        price_per_unit = request.form.get('price_per_unit')
        expiry_date_str = request.form.get('expiry_date')

        # Convert the expiry date string to a date object
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()

        # Create a new medicine entry
        new_medicine = Pharmacy(
            medicine_name=medicine_name,
            stock_quantity=stock_quantity,
            price_per_unit=price_per_unit,
            expiry_date=expiry_date
        )

        # Add the new medicine to the database
        db.session.add(new_medicine)
        db.session.commit()

        # Redirect to the inventory page
        return redirect(url_for('pharmacy.view_inventory'))

    return render_template('add_medicine.html')
@staff_bp.route("/dashboard")
def staff_dashboard():
    total_patients = Patient.query.count()
    total_medicines = Pharmacy.query.count()

    return render_template("dashboard_staff.html", 
                           total_patients=total_patients, 
                           total_medicines=total_medicines)

@staff_bp.route("/check-in")
def check_in():
    return "Check-in management coming soon!"

@patient_bp.route('/dashboard', methods=['GET'])
@login_required
def patient_dashboard():
    if current_user.role.name.lower() != 'patient':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home')) 
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    payments = Payment.query.filter_by(patient_id=current_user.id).all()

    if not patient:
        flash("Patient profile not found.", "danger")
        return redirect(url_for('main_routes.home'))
    appointments = Appointment.query.filter_by(patient_id=patient.id).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient.id).all()
    print(f"Patient ID: {patient.id}")
    print("Appointments:")
    print("Prescriptions:", prescriptions)
    for appt in appointments:
        print(f"  ID: {appt.id}, Doctor ID: {appt.doctor_id}, Date: {appt.appointment_date}, Status: {appt.status}")
    return render_template("dashboard_patient.html", appointments=appointments, patient=patient, prescriptions=prescriptions, payments=payments)

@patient_bp.route('/make_payment', methods=['GET', 'POST'])
@login_required
def make_payment():
    if request.method == 'POST':
        try:
            amount = request.form.get('amount')
            payment_method = request.form.get('payment_method')
            category = request.form.get('category')

            if not amount or not payment_method or not category:
                flash('All fields are required!', 'danger')
                return redirect(url_for('patient.make_payment'))

            try:
                amount = float(amount)
                if amount <= 0:
                    flash('Invalid amount. Please enter a positive value.', 'danger')
                    return redirect(url_for('patient.make_payment'))
            except ValueError:
                flash('Invalid amount. Please enter a valid number.', 'danger')
                return redirect(url_for('patient.make_payment'))

            new_payment = Payment(
                patient_id=current_user.id,
                amount=amount,
                payment_method=payment_method,
                payment_status='Pending',
                payment_date=datetime.now(),
                category=category
            )
            db.session.add(new_payment)
            db.session.commit()

            flash('Payment initiated successfully! Please wait for confirmation.', 'success')
            return redirect(url_for('patient.patient_dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('patient.make_payment'))

    return render_template('make_payment.html')

@patient_bp.route('/appointments/book', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        appointment_date_str = request.form['appointment_date']
        appointment_date = datetime.strptime(appointment_date_str, "%Y-%m-%dT%H:%M")
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient:
            flash("Patient profile not found.", "danger")
            return redirect(url_for('patient.patient_dashboard'))
        new_appointment = Appointment(
            patient_id=patient.id,  
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
def medical_records_patient():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    records = MedicalRecord.query.filter_by(patient_id=patient.id).all()
    return render_template('medical_records.html',  patient=patient, records=records)

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
        password = form.password.data or "default123" 
        role_id = int(form.role.data)  

        if not role_id:
            flash("Please select a role.", "danger")
            return render_template('add_user.htmlpassword', form=form)

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("Username or Email already exists. Please choose a different one.", 'danger')
            return redirect(url_for('admin.add_user'))  

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8') 

        try:
            new_user = User(username=username, email=email, password=hashed_password, role_id=role_id)
            db.session.add(new_user)
            db.session.commit() 
            if role_id == 2:  
                first_name = request.form.get('doctor_first_name')
                last_name = request.form.get('doctor_last_name', "")
                specialization = request.form.get('doctor_specialization')
                contact_number = request.form.get('doctor_contact_number')

                if not first_name or not specialization:
                    flash("Doctor requires first name and specialization!", "danger")
                    db.session.delete(new_user)
                    db.session.commit()
                    return redirect(url_for('admin.add_user'))

                doctor = Doctor(
                    user_id=new_user.id,  
                    first_name=first_name,
                    last_name=last_name,
                    specialization=specialization,
                    contact_number=contact_number,
                    email=email  
                )
                db.session.add(doctor)

            elif role_id == 3:  
                first_name = request.form.get('patient_first_name')
                last_name = request.form.get('patient_last_name', "")
                date_of_birth_str = request.form.get('patient_date_of_birth')  
                gender = request.form.get('patient_gender')
                contact_number = request.form.get('patient_contact_number')

                if not first_name or not date_of_birth_str or not gender:
                    flash("Patient requires first name, DOB, and gender!", "danger")
                    db.session.delete(new_user)
                    db.session.commit()
                    return redirect(url_for('admin.add_user'))

                try:
                    date_of_birth = datetime.strptime(date_of_birth_str, "%Y-%m-%d").date() 
                except ValueError:
                    flash("Invalid date format! Use YYYY-MM-DD.", "danger")
                    db.session.delete(new_user)
                    db.session.commit()
                    return redirect(url_for('admin.add_user'))

                patient = Patient(
                    user_id=new_user.id,
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=date_of_birth, 
                    gender=gender,
                    contact_number=contact_number
                )
                db.session.add(patient)

            elif role_id == 4:  
                position = request.form.get('staff_position')
                contact_number = request.form.get('staff_contact_number')

                if not position:
                    flash("Staff requires a position!", "danger")
                    db.session.delete(new_user)
                    db.session.commit()
                    return redirect(url_for('admin.add_user'))

                staff = Staff(
                    user_id=new_user.id,  
                    position=position,
                    contact_number=contact_number
                )
                db.session.add(staff)
                
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
    
    try:
        doctor = Doctor.query.filter_by(user_id=user_id).first()
        if doctor:
            appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()
            for appointment in appointments:
                db.session.delete(appointment) 
            db.session.delete(doctor)
        patient = Patient.query.filter_by(user_id=user_id).first()
        if patient:
            appointments = Appointment.query.filter_by(patient_id=patient.id).all()
            for appointment in appointments:
                db.session.delete(appointment)  
            db.session.delete(patient)
        staff = Staff.query.filter_by(user_id=user_id).first()
        if staff:
            db.session.delete(staff)
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    return redirect(url_for('admin.manage_users'))

@admin_routes.route('/manage_appointments')
@login_required
def manage_appointments():
    if current_user.role.name.lower() != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))

    appointments = db.session.query(
        Appointment.id.label('id'),
        Appointment.appointment_date.label('appointment_date'),
        Appointment.status.label('status'),
        Patient.first_name.label('patient_name'),
        Doctor.first_name.label('doctor_name')
    ).join(Patient, Patient.id == Appointment.patient_id) \
     .join(Doctor, Doctor.id == Appointment.doctor_id) \
     .all()
     
    print(url_for('admin.manage_appointments'))

    return render_template('manage_appointments.html', appointments=appointments)

@admin_routes.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    if current_user.role.name.lower() != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))

    appointment = Appointment.query.get_or_404(appointment_id)

    try:
        db.session.delete(appointment)
        db.session.commit()
        flash('Appointment deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting appointment: {str(e)}', 'danger')

    return redirect(url_for('admin.manage_appointments'))

@admin_routes.route('/manage_billing', methods=['GET'])
@login_required
def manage_billing():
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Payment.query

    if status:
        query = query.filter(Payment.payment_status == status)
    if start_date:
        query = query.filter(Payment.payment_date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Payment.payment_date <= datetime.strptime(end_date, '%Y-%m-%d'))

    payments = query.all()
    
    return render_template('manage_billing.html', payments=payments, status=status, start_date=start_date, end_date=end_date)

@admin_routes.route('/mark_paid/<int:payment_id>', methods=['POST'])
@login_required
def mark_paid(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    payment.payment_status = 'Paid'
    db.session.commit()
    flash('Payment marked as Paid!', 'success')
    return redirect(url_for('admin.manage_billing'))

@admin_routes.route('/add_payment', methods=['GET', 'POST'])
@login_required
def add_payment():
    if current_user.role.name.lower() != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))

    patients = Patient.query.all()

    if request.method == 'POST':
        try:
            patient_id = int(request.form.get('patient_id'))
            amount = float(request.form.get('amount'))
            payment_method = request.form.get('payment_method')
            payment_status = request.form.get('payment_status')

            # Validate input
            if not (patient_id and amount > 0 and payment_method and payment_status):
                flash('Invalid data. Please check your inputs.', 'danger')
                return render_template('add_payment.html', patients=patients)

            transaction_id = str(uuid.uuid4())

            payment = Payment(
                patient_id=patient_id,
                amount=amount,
                payment_method=payment_method,
                payment_status=payment_status,
                transaction_id=transaction_id
            )

            db.session.add(payment)
            db.session.commit()
            flash('Payment added successfully!', 'success')
            return redirect(url_for('admin.manage_billing'))

        except ValueError:
            flash('Invalid amount or patient ID.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')

    return render_template('add_payment.html', patients=patients)

@admin_routes.route('/edit_payment/<int:payment_id>', methods=['GET', 'POST'])
@login_required
def edit_payment(payment_id):
    if current_user.role.name.lower() != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))

    payment = Payment.query.get_or_404(payment_id)

    if request.method == 'POST':
        try:
            payment.amount = float(request.form.get('amount'))
            payment.payment_method = request.form.get('payment_method')
            payment.payment_status = request.form.get('payment_status')

            if payment.amount <= 0:
                flash('Amount must be greater than 0.', 'danger')
                return redirect(url_for('admin.edit_payment', payment_id=payment_id))

            db.session.commit()
            flash('Payment updated successfully!', 'success')
            return redirect(url_for('admin.manage_billing'))

        except ValueError:
            flash('Invalid amount.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating payment: {e}', 'danger')

    return render_template('edit_payment.html', payment=payment)

@admin_routes.route('/delete_payment/<int:payment_id>', methods=['POST'])
@login_required
def delete_payment(payment_id):
    if current_user.role.name.lower() != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('main_routes.home'))

    payment = Payment.query.get_or_404(payment_id)

    try:
        db.session.delete(payment)
        db.session.commit()
        flash('Payment deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting payment: {e}', 'danger')

    return redirect(url_for('admin.manage_billing'))

@admin_routes.route('/export_payments')
@login_required
def export_payments():
    payments = Payment.query.all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Payment ID', 'Patient Name', 'Amount', 'Payment Method', 'Status', 'Transaction ID', 'Date'])

    for payment in payments:
        writer.writerow([
            payment.id,
            f"{payment.patient.first_name} {payment.patient.last_name}" if payment.patient else "Unknown",
            payment.amount,
            payment.payment_method,
            payment.payment_status,
            payment.transaction_id or "N/A",
            payment.payment_date.strftime('%Y-%m-%d %H:%M:%S')
        ])

    output.seek(0)
    response = Response(output, content_type='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=payments.csv'
    return response

@admin_routes.route('/invoice/<int:payment_id>')
@login_required
def view_invoice(payment_id):
    payment = Payment.query.get(payment_id)
    if not payment:
        return "Invoice not found", 404
    return render_template('invoice.html', payment=payment)


@admin_routes.route('/generate_invoice/<payment_id>', methods=['GET'])
@login_required
def generate_invoice(payment_id):
    if current_user.role.name.lower() != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('admin.manage_billing'))
    
    try:
        if payment_id == 'all':
            payments = Payment.query.filter_by(payment_status='Paid').all()
            flash(f'{len(payments)} invoices generated successfully.', 'success')
        else:
            payment = Payment.query.get(payment_id)
            if not payment:
                flash('Payment not found.', 'danger')
                return redirect(url_for('admin.manage_billing'))

            flash(f'Invoice generated for Payment ID: {payment_id}', 'success')

        return redirect(url_for('admin.manage_billing'))

    except Exception as e:
        flash(f'Error generating invoice: {e}', 'danger')
        return redirect(url_for('admin.manage_billing'))

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
            return redirect(url_for('patient.patient_dashboard'))
        elif user.role.name.lower() == 'staff':
            return redirect(url_for('staff.staff_dashboard'))

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
            new_doctor = Doctor(
                user_id=new_user.id,
                first_name=request.form.get('doctor_first_name', new_user.username),
                last_name=request.form.get('doctor_last_name', ""),
                email=new_user.email,
                specialization=request.form.get('doctor_specialization', "General"),
                contact_number=request.form.get('doctor_contact_number', "")
            )
            db.session.add(new_doctor)

        elif role.name.lower() == "patient":
            new_patient = Patient(
                user_id=new_user.id,
                first_name=request.form.get('patient_first_name', new_user.username),
                last_name=request.form.get('patient_last_name', ""),
                date_of_birth=datetime.strptime(request.form.get('patient_date_of_birth', '2000-01-01'), '%Y-%m-%d'),
                gender=request.form.get('patient_gender', "Other"),
                contact_number=request.form.get('patient_contact_number', ""),
                medical_history="None"
            )
            db.session.add(new_patient)

        elif role.name.lower() == "staff":
            new_staff = Staff(
                user_id=new_user.id,
                position=request.form.get('staff_position', "Receptionist"),
                contact_number=request.form.get('staff_contact_number', "")
            )
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
        flash('Access denied. Only doctors can access this page.', 'danger')
        return redirect(url_for('main_routes.home'))

    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        flash("Doctor profile not found!", "danger")
        return redirect(url_for('main_routes.home'))

    appointments = Appointment.query.filter_by(doctor_id=doctor.id).order_by(Appointment.appointment_date).all()
    
    today = datetime.today().date()
    todays_appointments = [appt for appt in appointments if appt.appointment_date.date() == today]

    prescriptions = Prescription.query.filter_by(doctor_id=doctor.id).all()
    patients = list({appt.patient for appt in appointments})

    return render_template(
        'dashboard_doctor.html',
        doctor=doctor,
        appointments=appointments,
        todays_appointments=todays_appointments,
        prescriptions=prescriptions,
        patients=patients
    )
    
@doctor_routes.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    if current_user.role.name.lower() != 'doctor':
        flash('Access denied. Only doctors can update profiles.', 'danger')
        return redirect(url_for('main_routes.home'))

    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        flash('Doctor profile not found.', 'danger')
        return redirect(url_for('main_routes.doctor_dashboard'))

    doctor.first_name = request.form.get('first_name')
    doctor.last_name = request.form.get('last_name')
    doctor.specialization = request.form.get('specialization')
    doctor.contact_number = request.form.get('contact_number')
    doctor.email = request.form.get('email')

    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('main_routes.doctor_dashboard'))

@doctor_routes.route('/reschedule/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def reschedule_appointment(appointment_id):
    if current_user.role.name.lower() != 'doctor':
        flash('Access denied. Only doctors can reschedule appointments.', 'danger')
        return redirect(url_for('main_routes.home'))

    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.doctor_id != doctor.id:
        flash('You do not have permission to reschedule this appointment.', 'danger')
        return redirect(url_for('main_routes.doctor_dashboard'))

    if request.method == 'POST':
        new_date = request.form.get('appointment_date')
        if new_date:
            appointment.appointment_date = datetime.strptime(new_date, '%Y-%m-%dT%H:%M')  
            appointment.status = 'Rescheduled'
            db.session.commit()
            flash('Appointment rescheduled successfully!', 'success')
            return redirect(url_for('main_routes.doctor_dashboard'))

    return render_template('reschedule_appointment.html', appointment=appointment)

@doctor_routes.route('/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    if current_user.role.name.lower() != 'doctor':
        flash('Access denied. Only doctors can cancel appointments.', 'danger')
        return redirect(url_for('main_routes.home'))

    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.doctor_id != doctor.id:
        flash('You do not have permission to cancel this appointment.', 'danger')
        return redirect(url_for('main_routes.doctor_dashboard'))

    appointment.status = 'Cancelled'
    db.session.commit()
    flash('Appointment cancelled successfully!', 'success')
    return redirect(url_for('main_routes.doctor_dashboard'))

@doctor_routes.route('/appointment/complete/<int:appointment_id>', methods=['POST'])
@login_required
def complete_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'Completed'
    db.session.commit()
    flash('Appointment marked as completed.', 'success')
    return redirect(url_for('main_routes.doctor_dashboard'))

@doctor_routes.route('/add_prescription', methods=['GET', 'POST'])
@login_required
def add_prescription():
    if current_user.role.name.lower() != 'doctor':
        flash('Access denied. Only doctors can add prescriptions.', 'danger')
        return redirect(url_for('main_routes.home'))

    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    patients = Patient.query.all()

    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        medicine_name = request.form.get('medicine_name')
        dosage = request.form.get('dosage')

        date_prescribed_str = request.form.get('date_prescribed')
        if not date_prescribed_str:
            flash('Date prescribed is required.', 'danger')
            return redirect(request.referrer)

        try:
            date_prescribed = datetime.strptime(date_prescribed_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format for "Date Prescribed".', 'danger')
            return redirect(request.referrer)

        end_date_str = request.form.get('end_date')
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid date format for "End Date".', 'danger')
                return redirect(request.referrer)

        prescription = Prescription(
            patient_id=patient_id,
            doctor_id=doctor.id,
            medicine_name=medicine_name,
            dosage=dosage,
            date_prescribed=date_prescribed,
            end_date=end_date
        )

        db.session.add(prescription)
        db.session.commit()
        flash('Prescription added successfully!', 'success')
        return redirect(url_for('main_routes.doctor_dashboard'))

    return render_template('doctor_dashboard.html', patients=patients)

@doctor_routes.route('/prescription/view/<int:prescription_id>', methods=['GET'])
@login_required
def view_prescription(prescription_id):
    prescription = Prescription.query.get_or_404(prescription_id)
    return render_template('view_prescription.html', prescription=prescription)

@patient_bp.route('/prescription/view/<int:prescription_id>', methods=['GET'])
@login_required
def view_prescription_patient(prescription_id):
    prescription = Prescription.query.get_or_404(prescription_id)

    patient = Patient.query.filter_by(user_id=current_user.id).first()

    if not patient or prescription.patient_id != patient.id:
        flash("You are not authorized to view this prescription.", "danger")
        return redirect(url_for('patient.patient_dashboard'))

    return render_template('view_prescription.html', prescription=prescription)

@doctor_routes.route('/prescription/edit/<int:prescription_id>', methods=['GET', 'POST'])
@login_required
def edit_prescription(prescription_id):
    prescription = Prescription.query.get_or_404(prescription_id)
    if current_user.role not in ['doctor', 'admin']:
        flash("You are not authorized to edit this prescription.", "danger")
        return redirect(url_for('patient.patient_dashboard'))
    
    if request.method == 'POST':
        medication = request.form.get('medication')
        dosage = request.form.get('dosage')
        instructions = request.form.get('instructions', '')
        date_prescribed_str = request.form.get('date_prescribed')

        if not medication or not dosage or not date_prescribed_str:
            flash('All fields are required!', 'danger')
            return redirect(request.url)

        try:
            date_prescribed = datetime.strptime(date_prescribed_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format', 'danger')
            return redirect(request.url)

        prescription.medicine_name = medication
        prescription.dosage = dosage
        prescription.instructions = instructions
        prescription.date_prescribed = date_prescribed

        try:
            db.session.commit()  
            flash('Prescription updated successfully', 'success')
            return redirect(url_for('doctor_routes.view_prescription', prescription_id=prescription.id))
        except Exception as e:
            db.session.rollback() 
            flash(f'Error updating prescription: {str(e)}', 'danger')
            return redirect(request.url)

    return render_template('edit_prescription.html', prescription=prescription)
@doctor_routes.route('/delete_prescription/<int:prescription_id>', methods=['POST'])
@login_required
def delete_prescription(prescription_id):
    if current_user.role.name.lower() != 'doctor':
        flash('Access denied. Only doctors can delete prescriptions.', 'danger')
        return redirect(url_for('main_routes.home'))

    prescription = Prescription.query.get(prescription_id)
    if prescription:
        db.session.delete(prescription)
        db.session.commit()
        flash('Prescription deleted successfully!', 'success')
    else:
        flash('Prescription not found.', 'danger')

    return redirect(url_for('main_routes.doctor_dashboard'))

@doctor_routes.route('/add_medical_record/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def add_medical_record(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()

    
    if request.method == 'POST':
        record_type = request.form['record_type']
        treatment_plan = request.form['treatment_plan']
        description = request.form.get('description', '')
        record_date_str = request.form['record_date']
        record_date = datetime.strptime(record_date_str, "%Y-%m-%d")

        new_record = MedicalRecord(
            patient_id=patient.id,
            doctor_id=doctor.id,
            record_date=record_date,
            record_type=record_type,
            treatment_plan=treatment_plan,
            description=description
        )

        db.session.add(new_record)
        db.session.commit()
        flash('Medical record added successfully!', 'success')
        return redirect(url_for('main_routes.doctor_dashboard'))

    return render_template('add_medical_record.html', patient=patient)

@doctor_routes.route('/medical_records/<int:patient_id>')
@login_required
def medical_records(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    records = MedicalRecord.query.filter_by(patient_id=patient.id).all()

    return render_template("medical_records.html", patient=patient, records=records)

@doctor_routes.route('/update_medical_record/<int:medical_record_id>', methods=['GET', 'POST'])
@login_required
def update_medical_record(medical_record_id):
    record = MedicalRecord.query.get_or_404(medical_record_id)

    if current_user.role.name.lower() != 'doctor' or record.doctor.user_id != current_user.id:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('doctor_routes.medical_records', patient_id=record.patient_id))

    if request.method == 'POST':
        record.record_type = request.form['record_type']
        record.treatment_plan = request.form['treatment_plan']
        record.description = request.form.get('description', '')

        db.session.commit()
        flash('Medical record updated successfully!', 'success')
        return redirect(url_for('doctor_routes.medical_records', patient_id=record.patient_id))

    return render_template("update_medical_record.html", record=record)


@doctor_routes.route('/delete_medical_record/<int:medical_record_id>', methods=['POST'])
@login_required
def delete_medical_record(medical_record_id):
    record = MedicalRecord.query.get_or_404(medical_record_id)

    if current_user.role.name.lower() != 'doctor' or record.doctor.user_id != current_user.id:
        flash("Unauthorized action!", "danger")
        return redirect(url_for('doctor_routes.medical_records', patient_id=record.patient_id))

    db.session.delete(record)
    db.session.commit()
    flash('Medical record deleted successfully!', 'success')

    return redirect(url_for('doctor_routes.medical_records', patient_id=record.patient_id))
