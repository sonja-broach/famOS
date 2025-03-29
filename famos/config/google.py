import os

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://127.0.0.1:5000/account/integrations/google/callback')

# Define the scopes we need - keep them minimal and consistent
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/tasks',  # Full access to Tasks
    'https://www.googleapis.com/auth/tasks.readonly',  # Read-only access to Tasks
    'https://www.googleapis.com/auth/calendar.readonly',  # Read-only access to Calendar
    'https://www.googleapis.com/auth/calendar',  # Full access to Calendar
    'https://www.googleapis.com/auth/drive.readonly',  # Read-only access to Drive
    'https://www.googleapis.com/auth/drive.file'  # Per-file access to Drive
]
