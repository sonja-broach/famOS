from famos import create_app, db

app = create_app()
with app.app_context():
    db.drop_all()  # Clean slate
    db.create_all()  # Create all tables
    print("Database initialized successfully!")
