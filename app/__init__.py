from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_session import Session
from flask import url_for, redirect

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'fdhtyribynuypojm'  
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['SESSION_TYPE'] = 'filesystem'  
    app.config['SESSION_PERMANENT'] = True
    app.config['SESSION_FILE_DIR'] = './flask_session/'
    Session(app)  
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
    login_manager.login_view = 'main_routes.login'  
    login_manager.session_protection = "strong"  
    from .routes import main_routes, admin_routes, patient_bp, doctor_routes
    app.register_blueprint(main_routes)
    app.register_blueprint(admin_routes, url_prefix='/admin')  
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_routes, url_prefix='/doctor')
    return app

from .models import User  
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for("main_routes.login", role="admin")) 