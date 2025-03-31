from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta, datetime
from config import Config

# Initialize Flask extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
sess = Session()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    
    # Set default configuration
    app.config.from_mapping(
        # Default secret that should be overridden in instance config
        SECRET_KEY='dev',
        # Store the database in the instance folder
        DATABASE=os.path.join(app.instance_path, 'famos.sqlite'),
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.instance_path, 'famos.sqlite'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # Session configuration
        SESSION_TYPE='filesystem',
        PERMANENT_SESSION_LIFETIME=timedelta(days=31),
        SESSION_FILE_DIR=os.path.join(app.instance_path, 'flask_session')
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_object('config.Config')
    else:
        # Load the test config if passed in
        app.config.update(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
        os.makedirs(app.config['SESSION_FILE_DIR'])
    except OSError:
        pass

    # Initialize Flask-Session
    sess.init_app(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Set up logging
    if not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Delete existing log file if it exists
        log_file = 'logs/famos.log'
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
            except OSError:
                pass
                
        file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
    
    # Register blueprints
    from famos.routes import auth, main, family, tasks, calendar, contacts, account, integrations, dashboard
    app.register_blueprint(auth.bp, url_prefix='/auth')
    app.register_blueprint(main.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(family.bp, url_prefix='/family')
    app.register_blueprint(tasks.bp, url_prefix='/tasks')
    app.register_blueprint(calendar.bp, url_prefix='/calendar')
    app.register_blueprint(contacts.bp, url_prefix='/contacts')
    app.register_blueprint(account.bp, url_prefix='/account')
    app.register_blueprint(integrations.bp)
    
    # Custom template filters
    @app.template_filter('format_date')
    def format_date(date_str):
        if not date_str:
            return ""
            
        app.logger.debug(f"Formatting date: {date_str}")
        
        try:
            # Parse the date string - try different formats
            try:
                date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                app.logger.debug(f"Parsed as format 1: %Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
                    app.logger.debug(f"Parsed as format 2: %Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                        app.logger.debug(f"Parsed as format 3: %Y-%m-%d")
                    except ValueError:
                        try:
                            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
                            app.logger.debug(f"Parsed as format 4: %Y-%m-%dT%H:%M:%S%z")
                        except ValueError:
                            try:
                                date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                                app.logger.debug(f"Parsed as format 5: %Y-%m-%d %H:%M:%S")
                            except ValueError:
                                app.logger.error(f"Could not parse date: {date_str}")
                                return date_str
            
            # Convert to local timezone for display
            if hasattr(date, 'tzinfo') and date.tzinfo is not None:
                date = date.astimezone()
            
            # Get current date for comparison
            now = datetime.now()
            
            # If it's today
            if date.date() == now.date():
                result = f"Today at {date.strftime('%-I:%M %p')}"
            # If it's tomorrow
            elif date.date() == (now + timedelta(days=1)).date():
                result = f"Tomorrow at {date.strftime('%-I:%M %p')}"
            # If it's within 6 days
            elif 0 < (date.date() - now.date()).days < 6:
                result = f"{date.strftime('%A')} at {date.strftime('%-I:%M %p')}"
            # Otherwise show full date
            else:
                result = date.strftime("%b %-d at %-I:%M %p")
            
            app.logger.debug(f"Formatted date: {result}")
            return result
            
        except Exception as e:
            app.logger.error(f"Error formatting date {date_str}: {str(e)}")
            return date_str
    
    @login_manager.user_loader
    def load_user(user_id):
        from famos.models import User
        return User.query.get(int(user_id))
    
    # Import models
    from famos.models import User, Family, Task, Contact
    from famos.models.integrations import GoogleIntegration
    
    # Create tables for any models that don't exist yet
    with app.app_context():
        db.create_all()
        
    # Template filters
    @app.template_filter('datetime')
    def format_datetime(value):
        if not value:
            return ''
        try:
            if isinstance(value, str):
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            else:
                dt = value
            return dt.strftime('%B %d, %Y %I:%M %p')
        except:
            return value

    return app
