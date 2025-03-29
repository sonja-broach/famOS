# famOS - Family Organization System

A comprehensive family management application built with Flask that helps families organize their daily lives.

## Features

- User Authentication
  - Email-based registration and login
  - Secure password hashing
  - Session management

- Dashboard
  - Quick actions for common tasks
  - Family activity overview
  - Task tracking
  - Upcoming events

- Family Management
  - Add and manage family members
  - Assign roles and permissions
  - Track family activities

## Technology Stack

- Backend: Python 3.13+ with Flask
- Database: SQLite with SQLAlchemy
- Frontend: Bootstrap 5 with Bootstrap Icons
- Testing: pytest with coverage reporting
- Logging: Built-in Flask logging with file rotation

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd famOS
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the development server:
```bash
flask run
```

## Testing

Run the test suite:
```bash
pytest -v --cov=famos tests/
```

## Project Structure

```
famOS/
├── famos/                  # Application package
│   ├── models/            # Database models
│   ├── routes/            # Route handlers
│   ├── templates/         # Jinja2 templates
│   ├── static/            # Static files
│   ├── forms/             # WTForms classes
│   └── utils/             # Utility functions
├── tests/                 # Test suite
├── migrations/            # Database migrations
├── logs/                  # Application logs
├── requirements.txt       # Project dependencies
└── config.py             # Configuration
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
