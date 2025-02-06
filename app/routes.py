from flask import Blueprint, render_template, flash, redirect, request, url_for
from flask_login import login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from .forms import LoginForm, RegistrationForm  
from .models import User, db, Role
from . import bcrypt 
main_routes = Blueprint('main_routes', __name__)

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
        return redirect(url_for('main_routes.dashboard'))

    return render_template('login.html', role=role, form=form)

@main_routes.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

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

        flash('Your account has been created!', 'success')
        return redirect(url_for('main_routes.login', role=role.name)) 

    return render_template('register.html', form=form)

@main_routes.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out!', 'info')
    return redirect(url_for('main_routes.home'))
