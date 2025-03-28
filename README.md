# famOS - Family Organization System

A modern family planner application to help families organize their daily lives, manage schedules, and coordinate activities.

## Features

- Family calendar and event management
- Task assignments and chore tracking
- Shopping lists and meal planning
- Family member profiles and schedules
- Shared notes and reminders
- Real-time updates and notifications

## Tech Stack

- Python/Flask backend
- SQLAlchemy for database management
- Flask-Login for user authentication
- Modern, responsive Bootstrap UI
- SQLite database (development)

## Installation

1. Clone the repository
2. Create a virtual environment:
```bash
python3 -m venv venv
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
flask db init
flask db migrate
flask db upgrade
```

6. Run the development server:
```bash
flask run
```

## Development

The application follows a modular structure:
- `famos/` - Main application package
  - `models/` - Database models
  - `routes/` - Route handlers
  - `templates/` - Jinja2 templates
  - `static/` - CSS, JavaScript, and assets
  - `utils/` - Utility functions

## License

MIT License - See LICENSE file for details
