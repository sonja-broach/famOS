import logging
from logging.handlers import RotatingFileHandler
import os

# Create a logger instance
logger = logging.getLogger('famos')

def setup_logger(app):
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Configure file handler
    file_handler = RotatingFileHandler(
        'logs/famos.log',
        maxBytes=10240,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Configure stream handler for console output
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    stream_handler.setLevel(logging.INFO)
    
    # Add handlers to both app and module loggers
    for handler in [file_handler, stream_handler]:
        app.logger.addHandler(handler)
        logger.addHandler(handler)
    
    app.logger.setLevel(logging.INFO)
    logger.setLevel(logging.INFO)
    
    logger.info('famOS startup')
