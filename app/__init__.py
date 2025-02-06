from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'fdhtyribynuypojm'  
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    bcrypt = Bcrypt()
    Migrate(app, db) 
    login_manager.init_app(app)
    
    login_manager.login_view = 'main_routes.login' 
    from .routes import main_routes
    app.register_blueprint(main_routes)

    return app

from .models import User  
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
