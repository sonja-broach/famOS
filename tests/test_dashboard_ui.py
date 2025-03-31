import pytest
from unittest.mock import patch, MagicMock
from famos.models.user import User
from famos.models.integrations import GoogleIntegration
from famos import db, create_app
from datetime import datetime, timezone, timedelta
from flask_login import login_user as flask_login_user
import random
import logging
import tempfile

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary directory for session files
    temp_dir = tempfile.mkdtemp()
    
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test',
        'SESSION_TYPE': 'filesystem',
        'SESSION_FILE_DIR': temp_dir,  # Use temp directory for session files
        'PERMANENT_SESSION_LIFETIME': 3600,
        'SESSION_PERMANENT': True,
        'LOGIN_DISABLED': False
    }
    
    app = create_app(test_config)
    
    # Create the database
    with app.app_context():
        db.create_all()
        yield app

@pytest.fixture
def _db(app):
    """Create a database session for each test."""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def authenticated_user(app, _db):
    """Create and authenticate a test user"""
    with app.app_context():
        user = User(email='test@example.com', first_name='Test', last_name='User')
        user.set_password('password')
        _db.session.add(user)
        _db.session.commit()
        
        # Create a Google integration for the user
        integration = GoogleIntegration(
            user_id=user.id,
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=datetime.now(timezone.utc).isoformat(),
            tasks_enabled=True
        )
        _db.session.add(integration)
        _db.session.commit()
        return user

@pytest.fixture
def auth_client(client, app, _db):
    with app.app_context():
        # Create test user
        user = User(email='test@example.com', first_name='Test', last_name='User')
        user.set_password('password')
        _db.session.add(user)
        _db.session.commit()
        
        # Create Google integration
        integration = GoogleIntegration(
            user_id=user.id,
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=datetime.now(timezone.utc).isoformat(),
            tasks_enabled=True
        )
        _db.session.add(integration)
        _db.session.commit()
        
        # Log in the user
        with client.session_transaction() as session:
            session['user_id'] = user.id
            session['_fresh'] = True
            session['selected_lists'] = ['Test List 1']  # Set default selected list
    
    return client

@pytest.fixture(autouse=True)
def setup_google_integration(app, authenticated_user):
    """Set up Google integration for the authenticated user."""
    with app.app_context():
        # Get a fresh instance of the user
        user = User.query.get(authenticated_user.id)
        
        integration = GoogleIntegration(
            user_id=user.id,
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            tasks_enabled=True
        )
        db.session.add(integration)
        db.session.commit()
        
        # Store the integration ID
        integration_id = integration.id
        
        # Clear the session
        db.session.remove()
        
        # Return fresh instances
        return GoogleIntegration.query.get(integration_id)

class TestDashboard:
    def test_dashboard_layout(self, auth_client, mock_google_service):
        """Test basic dashboard layout elements"""
        with patch('famos.routes.main.get_tasks_service', return_value=mock_google_service):
            response = auth_client.get('/dashboard')
            assert response.status_code == 200
            assert b'Test List 1' in response.data
            assert b'Test List 2' in response.data
    
    def test_tasks_display(self, auth_client, mock_google_service):
        """Test that tasks are displayed correctly"""
        with patch('famos.routes.main.get_tasks_service', return_value=mock_google_service):
            response = auth_client.get('/dashboard')
            assert response.status_code == 200
            assert b'Test Task 1' in response.data
            assert b'Test notes' in response.data
    
    def test_empty_tasks_message(self, auth_client, mock_google_service):
        """Test display when no tasks are present"""
        mock_service = mock_google_service
        mock_service.tasks.return_value.list.return_value.execute.return_value = {'items': []}
        
        with patch('famos.routes.main.get_tasks_service', return_value=mock_service):
            response = auth_client.get('/dashboard')
            assert response.status_code == 200
            assert b'No tasks found' in response.data
    
    def test_task_sorting(self, auth_client, mock_google_service):
        """Test task sorting functionality"""
        with patch('famos.routes.main.get_tasks_service', return_value=mock_google_service):
            response = auth_client.get('/dashboard?sort=due')
            assert response.status_code == 200
            assert b'Test Task 1' in response.data
    
    def test_list_filter_ui(self, auth_client, mock_google_service):
        """Test list filtering UI elements"""
        with patch('famos.routes.main.get_tasks_service', return_value=mock_google_service):
            response = auth_client.get('/dashboard')
            assert response.status_code == 200
            assert b'Test List 1' in response.data
            assert b'Test List 2' in response.data
    
    def test_list_selection_persistence(self, auth_client, mock_google_service):
        """Test that list selection persists in session"""
        with patch('famos.routes.main.get_tasks_service', return_value=mock_google_service):
            # Select specific lists
            response = auth_client.get('/dashboard?lists=Test+List+1&lists=Test+List+2')
            assert response.status_code == 200
            
            # Verify selections persist
            response = auth_client.get('/dashboard')
            assert response.status_code == 200
            assert b'Test List 1' in response.data
            assert b'Test List 2' in response.data
