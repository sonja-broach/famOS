import pytest
from flask_login import login_user, current_user
from flask import request, url_for
from famos import create_app, db
from famos.models.user import User
from famos.models.integrations import GoogleIntegration
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timedelta

@pytest.fixture(scope='function')
def app():
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-key',
        'LOGIN_DISABLED': False,
        'GOOGLE_CLIENT_ID': 'test-client-id',
        'GOOGLE_CLIENT_SECRET': 'test-client-secret'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def test_user(app):
    user = User(email='test@example.com', first_name='Test')
    with app.app_context():
        db.session.add(user)
        db.session.commit()
        # Refresh user to ensure it's attached to session
        db.session.refresh(user)
        return user

@pytest.fixture(scope='function')
def auth_client(app, client, test_user):
    with app.test_request_context():
        login_user(test_user)
    
    # Create a test client that will have the logged in user
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True
    
    return client

def test_dashboard_unauthenticated(client):
    """Test that unauthenticated users are redirected to login"""
    response = client.get('/dashboard')
    assert response.status_code == 302  # Should redirect to login
    assert '/login' in response.location

def test_dashboard_authenticated_no_integration(app, auth_client):
    """Test dashboard access for authenticated user without Google integration"""
    response = auth_client.get('/dashboard')
    assert response.status_code == 200
    assert b'No pending tasks' in response.data

@patch('famos.routes.dashboard.GoogleIntegration')
def test_dashboard_with_disconnected_integration(mock_integration, app, auth_client):
    """Test dashboard with a disconnected Google integration"""
    integration = MagicMock()
    integration.is_connected.return_value = False
    mock_integration.query.filter_by.return_value.first.return_value = integration
    
    response = auth_client.get('/dashboard')
    assert response.status_code == 200
    assert b'No pending tasks' in response.data

@patch('flask_login.login_required')  # Mock login_required at module level
@patch('flask_login.current_user')  # Mock current_user at module level
@patch('famos.routes.dashboard.GoogleIntegration')
@patch('famos.services.google_tasks.get_user_tasks')  # Mock where it's defined
@patch('famos.services.google_tasks.get_tasks_service')  # Mock the service creation
@patch('googleapiclient.discovery.build')  # Mock the Google API client
def test_dashboard_with_connected_integration(mock_build, mock_tasks_service, mock_get_user_tasks, mock_integration, mock_current_user, mock_login_required, app, test_user):
    """Test dashboard with a connected Google integration"""
    # Mock login_required to do nothing
    mock_login_required.return_value = lambda x: x
    
    # Mock current_user
    mock_current_user.id = test_user.id
    mock_current_user.first_name = test_user.first_name
    mock_current_user.is_authenticated = True
    
    # Create the integration instance
    integration = MagicMock()
    
    # Set up the integration properties
    type(integration).user_id = PropertyMock(return_value=test_user.id)
    type(integration).access_token = PropertyMock(return_value='test_token')
    type(integration).refresh_token = PropertyMock(return_value='test_refresh')
    type(integration).token_expiry = PropertyMock(return_value=datetime.now() + timedelta(hours=1))
    type(integration).tasks_enabled = PropertyMock(return_value=True)  # Make sure tasks are enabled
    integration.is_connected.return_value = True
    
    # Mock the integration query
    mock_query = MagicMock()
    mock_query.filter_by.return_value.first.return_value = integration
    mock_integration.query = mock_query
    
    # Mock the tasks that get_user_tasks will return
    mock_tasks = [
        {
            'title': 'Test Task 1',
            'due': '2025-03-30T00:00:00Z',
            'notes': 'Test notes',
            'list_name': 'Test List',
            'list_id': 'list1',
            'status': 'needsAction'
        }
    ]
    
    # Set up get_user_tasks mock to return the tasks
    mock_get_user_tasks.return_value = mock_tasks
    
    # Create a test client
    client = app.test_client()
    
    # Mock Flask app config
    app.config['GOOGLE_CLIENT_ID'] = 'test_client_id'
    app.config['GOOGLE_CLIENT_SECRET'] = 'test_client_secret'
    
    # Make the request in the app context
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True
        
        # Print debug information
        print(f"\nDebug Information:")
        print(f"User ID in test: {test_user.id}")
        print(f"Current user ID: {mock_current_user.id}")
        print(f"Integration user_id: {integration.user_id}")
        print(f"User is authenticated: {mock_current_user.is_authenticated}")
        print(f"Tasks enabled: {integration.tasks_enabled}")  # Add tasks_enabled debug info
        print(f"Integration is connected: {integration.is_connected()}")
        
        response = client.get('/dashboard')
        
        print(f"get_user_tasks called: {mock_get_user_tasks.called}")
        print(f"get_user_tasks call count: {mock_get_user_tasks.call_count}")
        print(f"get_user_tasks call args: {mock_get_user_tasks.call_args_list}")
        print(f"Integration is_connected() called: {integration.is_connected.called}")
        print(f"Integration is_connected() call count: {integration.is_connected.call_count}")
        print(f"Integration is_connected() call args: {integration.is_connected.call_args_list}")
        print(f"Response data: {response.data.decode('utf-8')}")
        
        # Verify get_user_tasks was called with the correct user ID
        assert mock_get_user_tasks.called, "get_user_tasks was not called"
        mock_get_user_tasks.assert_called_once_with(test_user.id)
        
        assert response.status_code == 200
        assert b'Test Task 1' in response.data
        assert b'Test notes' in response.data

@patch('famos.routes.dashboard.get_user_tasks')  # Mock where it's imported
@patch('famos.routes.dashboard.GoogleIntegration')
def test_dashboard_with_task_fetch_error(mock_integration, mock_get_tasks, app, auth_client):
    """Test dashboard when task fetching fails"""
    # Mock the integration
    integration = MagicMock()
    integration.is_connected.return_value = True
    mock_integration.query.filter_by.return_value.first.return_value = integration
    
    # Mock task fetching error
    mock_get_tasks.side_effect = Exception('Failed to fetch tasks')
    
    response = auth_client.get('/dashboard')
    assert response.status_code == 200
    assert b'No pending tasks' in response.data  # Should show empty tasks on error
