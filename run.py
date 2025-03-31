import logging
import os
from logging.handlers import RotatingFileHandler

# Set up logging before anything else
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Clean up old log files
for filename in os.listdir(LOGS_DIR):
    file_path = os.path.join(LOGS_DIR, filename)
    try:
        if os.path.isfile(file_path):
            os.unlink(file_path)
    except Exception as e:
        print(f'Error deleting {file_path}: {e}')

# Configure logging
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler
file_handler = RotatingFileHandler(
    os.path.join(LOGS_DIR, 'famos.log'),
    maxBytes=10485760,  # 10MB
    backupCount=10
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)

# Root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Remove any existing handlers
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Add handlers only to root logger
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

root_logger.info('=== STARTING APPLICATION (run.py) ===')

from famos import create_app
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
