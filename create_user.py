from famos import create_app, db
from famos.models.user import User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    # Create test user
    user = User(
        email='test@example.com',
        first_name='Test',
        last_name='User'
    )
    user.set_password('test123')
    db.session.add(user)
    db.session.commit()
    print(f"Created user: {user.email} with password: test123")
