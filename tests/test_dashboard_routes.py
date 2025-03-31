import pytest
from flask_login import login_user, current_user
from flask import request, url_for
from famos import create_app, db
from famos.models.user import User
from famos.models.family import Family
from famos.models.integrations import GoogleIntegration
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timedelta
from pytz import UTC

@pytest.fixture(scope='function')
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-key',
        'LOGIN_DISABLED': False,
        'GOOGLE_CLIENT_ID': 'test-client-id',
        'GOOGLE_CLIENT_SECRET': 'test-client-secret',
        'SERVER_NAME': 'localhost'  # Add this to fix URL generation
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def authenticated_client(client, app):
    with app.test_request_context():
        # Create test user
        user = User(email='test@example.com', first_name='Test', last_name='User')
        user.set_password('password')
        db.session.add(user)
        db.session.flush()
        
        # Create default family
        family = Family(user_id=user.id, name='Test Family')
        db.session.add(family)
        db.session.commit()
        
        # Log in the user
        with client.session_transaction() as session:
            session['user_id'] = user.id
            session['_fresh'] = True
            session['selected_lists'] = ['Test List 1']  # Set default selected list
    
    return client

@pytest.fixture
def integration(app, authenticated_client):
    with app.test_request_context():
        user = User.query.filter_by(email='test@example.com').first()
        integration = GoogleIntegration(
            user_id=user.id,
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=datetime.now(UTC).replace(microsecond=0).isoformat(),  # Simple ISO format
            tasks_enabled=True
        )
        db.session.add(integration)
        db.session.commit()
        return integration

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def test_user(app):
    user = User(email='test@example.com', first_name='Test', last_name='User')
    with app.app_context():
        db.session.add(user)
        db.session.flush()
        
        # Create default family
        family = Family(user_id=user.id, name='Test Family')
        db.session.add(family)
        db.session.commit()
        
        # Refresh user to ensure it's attached to session
        db.session.refresh(user)
        return user

@pytest.fixture
def authenticated_user(app, client, test_user):
    with app.test_request_context():
        login_user(test_user)
    
    # Create a test client that will have the logged in user
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True
    
    return test_user

@pytest.fixture
def auth_client(app, client, test_user):
    with app.test_request_context():
        login_user(test_user)
    
    # Create a test client that will have the logged in user
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True
    
    return client

@pytest.fixture
def mock_google_service():
    mock_service = MagicMock()
    
    # Mock tasklists().list().execute()
    tasklists_mock = MagicMock()
    tasklists_mock.list = MagicMock()
    tasklists_mock.list.return_value = MagicMock()
    tasklists_mock.list.return_value.execute = MagicMock(return_value={
        'items': [
            {'id': 'list1', 'title': 'Test List 1'},
            {'id': 'list2', 'title': 'Test List 2'}
        ]
    })
    mock_service.tasklists = MagicMock(return_value=tasklists_mock)
    
    # Mock tasks().list().execute()
    tasks_mock = MagicMock()
    tasks_mock.list = MagicMock()
    tasks_mock.list.return_value = MagicMock()
    tasks_mock.list.return_value.execute = MagicMock(return_value={
        'items': [
            {
                'id': 'task1',
                'title': 'Test Task 1',
                'status': 'needsAction',
                'notes': 'Test notes',
                'due': datetime.now(UTC).replace(microsecond=0).isoformat(),
                'completed': None,
                'parent': None
            }
        ]
    })
    mock_service.tasks = MagicMock(return_value=tasks_mock)
    
    return mock_service

def test_dashboard_unauthenticated(client):
    """Test that unauthenticated users are redirected to login."""
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']

def test_dashboard_authenticated_no_integration(auth_client, authenticated_user):
    """Test dashboard when user has no Google integration."""
    # Remove existing integration
    with auth_client.application.app_context():
        integration = GoogleIntegration.query.filter_by(user_id=authenticated_user.id).first()
        if integration:
            db.session.delete(integration)
            db.session.commit()
    
    response = auth_client.get('/dashboard')
    assert response.status_code == 200
    assert b'Connect with Google' in response.data
    assert b'Connect your Google account to manage your tasks.' in response.data

def test_dashboard_with_disconnected_integration(auth_client, authenticated_user):
    """Test dashboard when Google integration is disconnected."""
    # Create a disconnected integration
    with auth_client.application.app_context():
        integration = GoogleIntegration(
            user_id=authenticated_user.id,
            access_token=None,
            refresh_token=None,
            tasks_enabled=True
        )
        db.session.add(integration)
        db.session.commit()
    
    response = auth_client.get('/dashboard')
    assert response.status_code == 200
    assert b'Reconnect Google Account' in response.data
    assert b'Your Google account needs to be reconnected.' in response.data

def test_dashboard_with_connected_integration(auth_client, authenticated_user, mock_google_service):
    """Test dashboard when Google integration is connected."""
    # Create a connected integration
    with auth_client.application.app_context():
        integration = GoogleIntegration(
            user_id=authenticated_user.id,
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=(datetime.now(UTC) + timedelta(hours=1)).replace(microsecond=0).isoformat(),
            tasks_enabled=True
        )
        db.session.add(integration)
        db.session.commit()
    
    with patch('famos.routes.main.get_tasks_service', return_value=mock_google_service), \
         patch('famos.routes.main.get_user_tasks', return_value=[{
             'id': 'task1',
             'title': 'Test Task 1',
             'status': 'needsAction',
             'notes': 'Test notes',
             'due': datetime.now(UTC).replace(microsecond=0).isoformat(),
             'completed': None,
             'parent': None,
             'list_id': 'list1',
             'list_name': 'Test List 1'
         }]):
        response = auth_client.get('/dashboard')
        assert response.status_code == 200
        # Test list selection
        assert b'Test List 1' in response.data
        assert b'Test List 2' in response.data
        # Test task display
        assert b'Test Task 1' in response.data
        assert b'Test notes' in response.data
        # Test task controls
        assert b'Show Completed Tasks' in response.data
        assert b'Apply Filter' in response.data

def test_dashboard_with_task_fetch_error(auth_client, authenticated_user, mock_google_service):
    """Test dashboard when there's an error fetching tasks."""
    # Create a connected integration
    with auth_client.application.app_context():
        integration = GoogleIntegration(
            user_id=authenticated_user.id,
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=(datetime.now(UTC) + timedelta(hours=1)).replace(microsecond=0).isoformat(),
            tasks_enabled=True
        )
        db.session.add(integration)
        db.session.commit()
    
    # Mock service to raise an error
    tasklists_mock = MagicMock()
    tasklists_mock.list = MagicMock()
    tasklists_mock.list.return_value = MagicMock()
    tasklists_mock.list.return_value.execute = MagicMock(side_effect=Exception('API Error'))
    mock_google_service.tasklists = MagicMock(return_value=tasklists_mock)
    
    with patch('famos.routes.main.get_tasks_service', return_value=mock_google_service), \
         patch('famos.routes.main.get_user_tasks', side_effect=Exception('API Error')):
        response = auth_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Error fetching tasks' in response.data

def test_dashboard_with_disabled_tasks(auth_client, authenticated_user):
    """Test dashboard when tasks are disabled."""
    # Create integration with tasks disabled
    with auth_client.application.app_context():
        integration = GoogleIntegration(
            user_id=authenticated_user.id,
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=(datetime.now(UTC) + timedelta(hours=1)).replace(microsecond=0).isoformat(),
            tasks_enabled=False
        )
        db.session.add(integration)
        db.session.commit()
    
    response = auth_client.get('/dashboard')
    assert response.status_code == 200
    assert b'Tasks are not enabled for this integration' in response.data

def test_dashboard_with_expired_token(auth_client, authenticated_user, mock_google_service):
    """Test dashboard when access token is expired."""
    # Create integration with expired token
    with auth_client.application.app_context():
        integration = GoogleIntegration(
            user_id=authenticated_user.id,
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=(datetime.now(UTC) - timedelta(hours=1)).replace(microsecond=0).isoformat(),
            tasks_enabled=True
        )
        db.session.add(integration)
        db.session.commit()
    
    with patch('famos.routes.main.get_tasks_service', return_value=mock_google_service), \
         patch('famos.routes.main.get_user_tasks', return_value=[{
             'id': 'task1',
             'title': 'Test Task 1',
             'status': 'needsAction',
             'notes': 'Test notes',
             'due': datetime.now(UTC).replace(microsecond=0).isoformat(),
             'completed': None,
             'parent': None,
             'list_id': 'list1',
             'list_name': 'Test List 1'
         }]):
        response = auth_client.get('/dashboard')
        assert response.status_code == 200
        # Should still work because token gets refreshed
        assert b'Test List 1' in response.data
        assert b'Test Task 1' in response.data
