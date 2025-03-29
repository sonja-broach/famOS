import pytest
from flask import session
from famos import create_app, db
from famos.models.user import User
from famos.models.family import Family
from werkzeug.security import generate_password_hash
from sqlalchemy.orm import scoped_session, sessionmaker
from config import TestConfig

@pytest.fixture(scope='function')
def app():
    app = create_app(TestConfig)
    return app

@pytest.fixture(scope='function')
def _db(app):
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def session(app, _db):
    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()
        
        session_factory = sessionmaker(bind=connection)
        session = scoped_session(session_factory)
        
        # Patch Flask-SQLAlchemy session
        _db.session = session
        
        yield session
        
        transaction.rollback()
        connection.close()
        session.remove()

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    return app.test_cli_runner()

def register_user(client, email="test@example.com", password="password", 
                 first_name="Test", last_name="User"):
    return client.post('/auth/register', data={
        'email': email,
        'password': password,
        'confirm_password': password,
        'first_name': first_name,
        'last_name': last_name,
        'csrf_token': 'test-csrf-token'
    }, follow_redirects=True)

def login_user(client, email="test@example.com", password="password"):
    return client.post('/auth/login', data={
        'email': email,
        'password': password,
        'csrf_token': 'test-csrf-token'
    }, follow_redirects=True)

class AuthActions:
    def __init__(self, client):
        self._client = client

    def register(self, email="test@example.com", password="password", 
                first_name="Test", last_name="User"):
        return register_user(self._client, email, password, first_name, last_name)

    def login(self, email="test@example.com", password="password"):
        return login_user(self._client, email, password)

@pytest.fixture(scope='function')
def auth(client):
    return AuthActions(client)

@pytest.fixture(scope='function')
def test_user(session):
    user = User(
        email='test@example.com',
        first_name='Test',
        last_name='User',
        password_hash=generate_password_hash('password')
    )
    session.add(user)
    session.commit()
    return user

@pytest.fixture(scope='function')
def test_family(session, test_user):
    family = Family(name='Test Family')
    session.add(family)
    session.commit()
    
    # Associate test user with the family
    test_user.family_id = family.id
    session.commit()
    return family

@pytest.fixture(scope='function')
def test_client(app, test_user):
    client = app.test_client()
    client.testing = True
    
    with client.session_transaction() as sess:
        sess['_csrf_token'] = 'test-csrf-token'
        sess['user_id'] = test_user.id
    
    return client
