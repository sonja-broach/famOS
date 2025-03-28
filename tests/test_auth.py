from famos.models import User
from tests.conftest import register_user, login_user

def test_register(client):
    """Test user registration"""
    # Test successful registration
    response = register_user(client)
    assert b'Registration successful!' in response.data
    
    # Test duplicate email
    response = register_user(client)
    assert b'Email already registered' in response.data
    
    # Test invalid email format
    response = register_user(client, email="invalid-email")
    assert b'Invalid email address' in response.data
    
    # Test password mismatch
    response = client.post('/auth/register', data={
        'email': 'another@example.com',
        'password': 'password1',
        'confirm_password': 'password2',
        'first_name': 'Test',
        'last_name': 'User'
    }, follow_redirects=True)
    assert b'Passwords must match' in response.data

def test_login_logout(client, app):
    """Test login and logout functionality"""
    # Register a user
    register_user(client)
    
    # Test successful login
    response = login_user(client)
    assert b'Welcome back!' in response.data
    
    # Test invalid password (should log out first)
    client.get('/auth/logout', follow_redirects=True)
    response = login_user(client, password="wrongpassword")
    assert b'Invalid email or password' in response.data
    
    # Test non-existent user
    response = login_user(client, email="nonexistent@example.com")
    assert b'Invalid email or password' in response.data
    
    # Test logout
    login_user(client)  # Log in first
    response = client.get('/auth/logout', follow_redirects=True)
    assert b'You have been logged out' in response.data

def test_login_required(client):
    """Test that protected routes require login"""
    # Try to access dashboard without login
    response = client.get('/dashboard', follow_redirects=True)
    assert b'Please log in to access this page' in response.data

def test_already_authenticated(client):
    """Test redirects for authenticated users"""
    # Register and login
    register_user(client)
    login_user(client)
    
    # Try to access login page while authenticated
    response = client.get('/auth/login')
    assert response.status_code == 302  # Should redirect
    
    # Try to access register page while authenticated
    response = client.get('/auth/register')
    assert response.status_code == 302  # Should redirect
