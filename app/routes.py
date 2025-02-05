from flask import Blueprint, render_template

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

@main_routes.route('/login')
def login():
    return render_template('login.html')

@main_routes.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')
