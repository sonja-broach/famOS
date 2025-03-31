import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from flask_sqlalchemy import SQLAlchemy
from famos import create_app, db
from famos.models import User, GoogleIntegration
from famos.services.google_tasks import get_tasks_service
from flask_login import login_user as flask_login_user

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-key'
    })
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def _db(app):
    """Create a fresh database for each test."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

@pytest.fixture
def auth_client(client, app, _db):
    with app.app_context():
        # Create test user
        user = User(email='test@example.com', first_name='Test', last_name='User')
        user.set_password('password')
        _db.session.add(user)
        _db.session.commit()
        
        # Store user ID for later use
        user_id = user.id
        
        # Clear session to prevent detached instance issues
        _db.session.remove()
        
        # Get fresh user instance
        user = User.query.get(user_id)
        
        # Create Google integration
        integration = GoogleIntegration(
            user_id=user.id,
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            tasks_enabled=True
        )
        _db.session.add(integration)
        _db.session.commit()
        
        # Log in the user
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)  # Flask-Login uses _user_id
            session['_fresh'] = True
            session.permanent = True  # Make session permanent
            session['selected_lists'] = ['list1']  # Set default selected list
    
    return client

@pytest.fixture
def authenticated_user(app, _db):
    """Create a test user."""
    with app.app_context():
        # Delete any existing users
        User.query.delete()
        _db.session.commit()
        
        user = User(
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        user.set_password('password')
        _db.session.add(user)
        _db.session.commit()
        return user

@pytest.fixture
def mock_google_service():
    mock_service = MagicMock()
    mock_tasklists = MagicMock()
    mock_tasks = MagicMock()
    
    # Mock task lists response
    mock_tasklists.list().execute.return_value = {
        'items': [
            {'id': 'list1', 'title': 'Test List 1'},
            {'id': 'list2', 'title': 'Test List 2'}
        ]
    }
    
    # Mock tasks response for each list
    def mock_tasks_list(tasklist=None, **kwargs):
        mock_response = MagicMock()
        if tasklist == 'list1':
            mock_response.execute.return_value = {
                'items': [
                    {
                        'id': 'task1',
                        'title': 'Test Task 1',
                        'status': 'needsAction',
                        'notes': 'Test notes',
                        'due': datetime.now(timezone.utc).isoformat()
                    }
                ]
            }
        else:
            mock_response.execute.return_value = {
                'items': [
                    {
                        'id': 'task2',
                        'title': 'Test Task 2',
                        'status': 'completed',
                        'completed': datetime.now(timezone.utc).isoformat()
                    }
                ]
            }
        return mock_response
    
    # Mock get task
    def mock_tasks_get(tasklist=None, task=None, **kwargs):
        mock_response = MagicMock()
        mock_response.execute.return_value = {
            'id': task,
            'title': 'Test Task 1',
            'status': 'needsAction',
            'notes': 'Test notes',
            'due': datetime.now(timezone.utc).isoformat()
        }
        return mock_response
    
    # Mock update task
    def mock_tasks_update(tasklist=None, task=None, body=None, **kwargs):
        mock_response = MagicMock()
        mock_response.execute.return_value = {
            'id': task,
            'title': 'Test Task 1',
            'status': body.get('status', 'needsAction'),
            'notes': body.get('notes', 'Test notes'),
            'due': body.get('due', datetime.now(timezone.utc).isoformat())
        }
        return mock_response
    
    mock_tasks.list = mock_tasks_list
    mock_tasks.get = mock_tasks_get
    mock_tasks.update = mock_tasks_update
    
    # Set up service mocks
    mock_service.tasklists.return_value = mock_tasklists
    mock_service.tasks.return_value = mock_tasks
    
    # Mock get_tasks_service to return our mock
    with patch('famos.routes.main.get_tasks_service', return_value=mock_service), \
         patch('famos.services.google_tasks.get_tasks_service', return_value=mock_service):
        yield mock_service

@pytest.fixture
def setup_google_integration(auth_client, authenticated_user, app, _db):
    """Set up Google integration for testing."""
    with app.app_context():
        # Delete any existing integrations
        GoogleIntegration.query.delete()
        _db.session.commit()
        
        integration = GoogleIntegration(
            user_id=authenticated_user.id,
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            tasks_enabled=True
        )
        _db.session.add(integration)
        _db.session.commit()
        return integration

@pytest.fixture(autouse=True)
def setup_db(app, _db):
    """Setup database for each test"""
    with app.app_context():
        _db.create_all()
        yield
        _db.session.remove()
        _db.drop_all()

def test_dashboard_with_no_lists_selected(auth_client, authenticated_user, mock_google_service, setup_google_integration):
    """Test dashboard view with no task lists selected."""
    with auth_client.application.app_context():
        # Clear any selected lists
        with auth_client.session_transaction() as session:
            session.pop('selected_lists', None)
        
        response = auth_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Test List 1' in response.data
        assert b'Test List 2' in response.data

def test_dashboard_with_specific_list(auth_client, authenticated_user, mock_google_service, setup_google_integration):
    """Test dashboard view with a specific list selected."""
    with auth_client.application.app_context():
        # Select a specific list by ID
        with auth_client.session_transaction() as session:
            session['selected_lists'] = ['list1']  # Use list ID instead of title
        
        response = auth_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Test List 1' in response.data
        assert b'Test Task 1' in response.data

def test_task_completion(auth_client, authenticated_user, mock_google_service, setup_google_integration):
    """Test marking a task as complete."""
    with auth_client.application.app_context():
        response = auth_client.post('/tasks/update', json={
            'task_list_id': 'list1',
            'task_id': 'task1',
            'status': 'completed'
        })
        assert response.status_code == 200
        assert response.json['id'] == 'task1'
        assert response.json['title'] == 'Test Task 1'
        assert response.json['status'] == 'completed'

def test_task_list_persistence(auth_client, authenticated_user, mock_google_service, setup_google_integration):
    """Test that selected task lists persist in session."""
    with auth_client.application.app_context():
        # Select specific lists by ID
        with auth_client.session_transaction() as session:
            session['selected_lists'] = ['list1']  # Use list ID instead of title
        
        response = auth_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Test List 1' in response.data
