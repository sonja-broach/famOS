import os
import tempfile
import pytest
from famos import create_app, db
from famos.models.user import User
from famos.models.family import Family
from famos.models.integrations import GoogleIntegration
from werkzeug.security import generate_password_hash
from sqlalchemy.orm import scoped_session, sessionmaker
from unittest.mock import MagicMock
from datetime import datetime, timezone
from flask_login import login_user as flask_login_user
import random

@pytest.fixture(autouse=True)
def _clean_db(app):
    """Clean database between tests."""
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-key',
        'SESSION_TYPE': 'filesystem',
        'SESSION_FILE_DIR': tempfile.mkdtemp(),  # Use temp directory for session files
        'PERMANENT_SESSION_LIFETIME': 3600,
        'SESSION_PERMANENT': True,
        'LOGIN_DISABLED': False,
        'GOOGLE_CLIENT_ID': 'test-client-id',
        'GOOGLE_CLIENT_SECRET': 'test-client-secret'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def authenticated_user(app):
    """A user for testing."""
    with app.app_context():
        # Create the user
        user = User(
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        # Create a family for the user
        family = Family(user_id=user.id, name='Test Family')
        user.family = family
        db.session.add(family)
        db.session.add(user)
        db.session.commit()
        
        # Store the user ID for later retrieval
        user_id = user.id
        
        # Clear the session to prevent detached instance issues
        db.session.remove()
        
        # Get a fresh instance of the user
        user = User.query.get(user_id)
        return user

@pytest.fixture
def auth_client(client, authenticated_user):
    """A test client with an authenticated user."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(authenticated_user.id)
        sess['_fresh'] = True
        sess.permanent = True
    
    with client.application.app_context():
        flask_login_user(authenticated_user, remember=True)
        db.session.add(authenticated_user)
        db.session.commit()
    
    return client

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def _db(app):
    """Create and configure a new database for each test."""
    with app.app_context():
        yield db

@pytest.fixture
def test_family(app, _db, authenticated_user):
    """Create a test family."""
    with app.app_context():
        family = Family(
            name="Test Family",
            created_by=authenticated_user.id
        )
        authenticated_user.family = family
        db.session.add(family)
        db.session.add(authenticated_user)
        db.session.commit()
        
        # Refresh the user to ensure it's attached to the session
        db.session.refresh(authenticated_user)
        return family

@pytest.fixture
def mock_google_service():
    """Create a mock Google Tasks service."""
    mock_service = MagicMock()
    
    # Mock tasklists().list().execute()
    mock_service.tasklists.return_value.list.return_value.execute.return_value = {
        'items': [
            {'id': 'list1', 'title': 'Test List 1'},
            {'id': 'list2', 'title': 'Test List 2'}
        ]
    }
    
    # Mock tasks().list().execute()
    mock_service.tasks.return_value.list.return_value.execute.return_value = {
        'items': [
            {
                'id': 'task1',
                'title': 'Test Task 1',
                'notes': 'Test notes',
                'due': datetime.now(timezone.utc).isoformat(),
                'status': 'needsAction',
                'list_id': 'list1',
                'list_name': 'Test List 1'
            }
        ]
    }
    
    return mock_service

def register_user(client, email="test@example.com", password="password", 
                first_name="Test", last_name="User"):
    return client.post('/auth/register', data={
        'email': email,
        'password': password,
        'confirm_password': password,
        'first_name': first_name,
        'last_name': last_name
    }, follow_redirects=True)

def login_user(client, email="test@example.com", password="password"):
    return client.post('/auth/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)

class AuthActions(object):
    def __init__(self, client):
        self._client = client

    def register(self, email="test@example.com", password="password", 
                first_name="Test", last_name="User"):
        return register_user(self._client, email, password, first_name, last_name)

    def login(self, email="test@example.com", password="password"):
        return login_user(self._client, email, password)

    def logout(self):
        return self._client.get('/auth/logout')

@pytest.fixture
def auth(client):
    return AuthActions(client)
