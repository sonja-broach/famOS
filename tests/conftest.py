import pytest
from famos import create_app, db
from config import TestConfig

@pytest.fixture
def app():
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

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
