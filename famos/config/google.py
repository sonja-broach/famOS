import os

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/account/integrations/google/callback')

# Define the scopes we need
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/calendar',  # Calendar access
    'https://www.googleapis.com/auth/tasks',     # Tasks access
    'https://www.googleapis.com/auth/drive.file' # Drive file access
]
