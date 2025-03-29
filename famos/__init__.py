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
    # Set instance path explicitly for famOS
    app.instance_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance')
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(app.instance_path, "famos.db")}')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = True  # Enable debug mode

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Set up login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from famos.models import User
        return User.query.get(int(user_id))

    # Set up logging
    setup_logger(app)

    # Import models
    from famos.models import User, Family, Task, Contact
    from famos.models.integrations import GoogleIntegration

    # Register blueprints
    from famos.routes import main, auth, family, tasks, calendar, contacts, account, integrations, dashboard
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp, url_prefix='/auth')
    app.register_blueprint(family.bp, url_prefix='/family')
    app.register_blueprint(tasks.bp, url_prefix='/tasks')
    app.register_blueprint(calendar.bp, url_prefix='/calendar')
    app.register_blueprint(contacts.bp, url_prefix='/contacts')
    app.register_blueprint(account.bp, url_prefix='/account')
    app.register_blueprint(integrations.bp)
    app.register_blueprint(dashboard.bp)

    # Create database tables
    with app.app_context():
        db.create_all()

    # Template filters
    @app.template_filter('datetime')
    def format_datetime(value):
        if not value:
            return ''
        from datetime import datetime
        try:
            if isinstance(value, str):
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            else:
                dt = value
            return dt.strftime('%B %d, %Y %I:%M %p')
        except:
            return value

    return app
