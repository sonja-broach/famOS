import pytest
from flask_login import login_user
from famos import create_app, db
from famos.models.user import User
from famos.models.integrations import GoogleIntegration
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-key',
        'GOOGLE_CLIENT_ID': 'test-client-id',
        'GOOGLE_CLIENT_SECRET': 'test-client-secret'
    })
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def _db(app):
    """Create database tables and return the database object"""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

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
            token_expiry=datetime.now() + timedelta(hours=1),
            tasks_enabled=True
        )
        # Mock is_connected to return True
        integration.is_connected = lambda: True
        _db.session.add(integration)
        _db.session.commit()
        
        # Keep the user attached to the session
        _db.session.refresh(user)
        return user

class TestDashboard:
    def test_dashboard_layout(self, app, client, authenticated_user, _db):
        """Test the basic layout of the dashboard"""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['_user_id'] = authenticated_user.id
                sess['_fresh'] = True
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            html = response.data.decode('utf-8')
            
            # Check main elements
            assert '<div class="container">' in html
            assert 'Dashboard' in html
        
    def test_tasks_display(self, app, client, authenticated_user, _db):
        """Test how tasks are displayed in the UI"""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['_user_id'] = authenticated_user.id
                sess['_fresh'] = True
            
            # Create a mock service that returns our test tasks
            mock_service = MagicMock()
            mock_tasklists = MagicMock()
            mock_tasks_list = MagicMock()
            
            # Set up the mock chain
            mock_service.tasklists.return_value = mock_tasklists
            mock_tasklists.list.return_value = mock_tasklists
            mock_tasklists.execute.return_value = {'items': [{'id': 'list1', 'title': 'Test List'}]}
            
            mock_service.tasks.return_value = mock_tasks_list
            mock_tasks_list.list.return_value = mock_tasks_list
            mock_tasks_list.execute.return_value = {'items': [
                {
                    'title': 'Test Task 1',
                    'due': '2025-03-30T00:00:00Z',
                    'notes': 'Test notes',
                    'status': 'needsAction'
                }
            ]}
            
            # Mock get_tasks_service to return our mock service
            with patch('famos.services.google_tasks.get_tasks_service') as mock_get_service:
                mock_get_service.return_value = mock_service
                
                # Make sure we have a valid integration in the database
                integration = GoogleIntegration.query.filter_by(user_id=authenticated_user.id).first()
                logger.debug(f"Integration found: {integration is not None}")
                if integration:
                    logger.debug(f"Integration tasks_enabled: {integration.tasks_enabled}")
                    logger.debug(f"Integration is_connected: {integration.is_connected()}")
                    logger.debug(f"Integration access_token: {integration.access_token}")
                    logger.debug(f"Integration refresh_token: {integration.refresh_token}")
                    logger.debug(f"Integration token_expiry: {integration.token_expiry}")
                assert integration is not None
                assert integration.tasks_enabled
                
                response = client.get('/dashboard')
                print(f"Mock service called: {mock_service.tasklists.called}")
                print(f"Mock service call count: {mock_service.tasklists.call_count}")
                print(f"Response HTML: {response.data.decode('utf-8')}")
                
                assert response.status_code == 200
                html = response.data.decode('utf-8')
                
                # Check task elements
                assert 'Test Task 1' in html
                assert 'Test notes' in html
        
    def test_empty_tasks_message(self, app, client, authenticated_user, _db):
        """Test the message shown when no tasks are present"""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['_user_id'] = authenticated_user.id
                sess['_fresh'] = True
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            html = response.data.decode('utf-8')
            
            assert 'No pending tasks' in html
        
    def test_task_sorting(self, app, client, authenticated_user, _db):
        """Test that tasks are properly sorted by due date"""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['_user_id'] = authenticated_user.id
                sess['_fresh'] = True
            
            # Create a mock service that returns our test tasks
            mock_service = MagicMock()
            mock_tasklists = MagicMock()
            mock_tasks_list = MagicMock()
            
            # Set up the mock chain
            mock_service.tasklists.return_value = mock_tasklists
            mock_tasklists.list.return_value = mock_tasklists
            mock_tasklists.execute.return_value = {'items': [{'id': 'list1', 'title': 'Test List'}]}
            
            mock_service.tasks.return_value = mock_tasks_list
            mock_tasks_list.list.return_value = mock_tasks_list
            mock_tasks_list.execute.return_value = {'items': [
                {
                    'title': 'Later Task',
                    'due': '2025-04-01T00:00:00Z',
                    'status': 'needsAction'
                },
                {
                    'title': 'Earlier Task',
                    'due': '2025-03-30T00:00:00Z',
                    'status': 'needsAction'
                }
            ]}
            
            # Mock get_tasks_service to return our mock service
            with patch('famos.services.google_tasks.get_tasks_service') as mock_get_service:
                mock_get_service.return_value = mock_service
                
                # Make sure we have a valid integration in the database
                integration = GoogleIntegration.query.filter_by(user_id=authenticated_user.id).first()
                logger.debug(f"Integration found: {integration is not None}")
                if integration:
                    logger.debug(f"Integration tasks_enabled: {integration.tasks_enabled}")
                    logger.debug(f"Integration is_connected: {integration.is_connected()}")
                    logger.debug(f"Integration access_token: {integration.access_token}")
                    logger.debug(f"Integration refresh_token: {integration.refresh_token}")
                    logger.debug(f"Integration token_expiry: {integration.token_expiry}")
                assert integration is not None
                assert integration.tasks_enabled
                
                response = client.get('/dashboard')
                print(f"Mock service called: {mock_service.tasklists.called}")
                print(f"Mock service call count: {mock_service.tasklists.call_count}")
                print(f"Response HTML: {response.data.decode('utf-8')}")
                
                assert response.status_code == 200
                html = response.data.decode('utf-8')
                
                # Check task order
                earlier_pos = html.find('Earlier Task')
                later_pos = html.find('Later Task')
                assert earlier_pos < later_pos, "Tasks should be sorted by due date"
