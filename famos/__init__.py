from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import os
import logging
from config import Config

# Initialize Flask extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    """Create and configure the app"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Get root logger and clear its handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Get logger
    logger = logging.getLogger('famos')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    
    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('logs/famos.log')
    
    # Set handler levels
    console_handler.setLevel(logging.DEBUG)
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatters and add it to handlers
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from famos.models import User
        return User.query.get(int(user_id))

    # Import models
    from famos.models import User, Family, Task, Contact
    from famos.models.integrations import GoogleIntegration

    # Register blueprints
    logger.info('Registering blueprints...')
    from famos.routes import main, auth, family, tasks, calendar, contacts, account, integrations, dashboard
    logger.info('Registering main blueprint...')
    app.register_blueprint(main.bp)
    logger.info(f'Main routes: {[rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("main")]}')
    
    logger.info('Registering auth blueprint...')
    app.register_blueprint(auth.bp, url_prefix='/auth')
    logger.info(f'Auth routes: {[rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("auth")]}')
    
    logger.info('Registering dashboard blueprint...')
    app.register_blueprint(dashboard.bp)
    logger.info(f'Dashboard routes: {[rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("dashboard")]}')
    
    logger.info('Registering family blueprint...')
    app.register_blueprint(family.bp, url_prefix='/family')
    logger.info(f'Family routes: {[rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("family")]}')
    
    logger.info('Registering tasks blueprint...')
    app.register_blueprint(tasks.bp, url_prefix='/tasks')
    logger.info(f'Tasks routes: {[rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("tasks")]}')
    
    logger.info('Registering calendar blueprint...')
    app.register_blueprint(calendar.bp, url_prefix='/calendar')
    logger.info(f'Calendar routes: {[rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("calendar")]}')
    
    logger.info('Registering contacts blueprint...')
    app.register_blueprint(contacts.bp, url_prefix='/contacts')
    logger.info(f'Contacts routes: {[rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("contacts")]}')
    
    logger.info('Registering account blueprint...')
    app.register_blueprint(account.bp, url_prefix='/account')
    logger.info(f'Account routes: {[rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("account")]}')
    
    logger.info('Registering integrations blueprint...')
    app.register_blueprint(integrations.bp)
    logger.info(f'Integrations routes: {[rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("integrations")]}')
    
    # Log all registered routes
    logger.info('All registered routes:')
    for rule in app.url_map.iter_rules():
        logger.info(f'Route: {rule.rule} -> {rule.endpoint}')
    
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

    logger.info('famOS application initialized')
    logger.info('=== Starting famOS Application ===')
    
    return app
