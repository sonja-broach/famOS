import logging
import os
from logging.handlers import RotatingFileHandler

# Set up logging before anything else
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler
file_handler = RotatingFileHandler('logs/famos.log', maxBytes=1024*1024, backupCount=10)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

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
