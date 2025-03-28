from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os
from config import Config
from famos.utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-this')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///famos.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Set up logging
    setup_logger(app)

    # Import models to ensure they are registered with SQLAlchemy
    from famos.models import User, Family, Task

    # Register blueprints
    from famos.routes import main, auth, family, tasks, calendar, contacts, account
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp, url_prefix='/auth')
    app.register_blueprint(family.bp, url_prefix='/family')
    app.register_blueprint(tasks.bp, url_prefix='/tasks')
    app.register_blueprint(calendar.bp, url_prefix='/calendar')
    app.register_blueprint(contacts.bp, url_prefix='/contacts')
    app.register_blueprint(account.bp, url_prefix='/account')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
