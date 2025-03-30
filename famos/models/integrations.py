from famos import db
from datetime import datetime
import logging

# Get a logger for this module
logger = logging.getLogger(__name__)

class GoogleIntegration(db.Model):
    """Model for storing Google integration settings."""
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    access_token = db.Column(db.String, nullable=True)
    refresh_token = db.Column(db.String, nullable=True)
    token_uri = db.Column(db.String, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    calendar_enabled = db.Column(db.Boolean, default=False)
    tasks_enabled = db.Column(db.Boolean, default=False)
    docs_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def is_connected(self):
        """Check if the integration is connected and valid."""
        logger.info(f"Checking connection status for user {self.user_id}")
        logger.info(f"Access token: {'Present' if self.access_token else 'Missing'}")
        logger.info(f"Refresh token: {'Present' if self.refresh_token else 'Missing'}")
        logger.info(f"Token expiry: {self.token_expiry}")
        
        if not self.access_token:
            logger.warning(f"No access token for user {self.user_id}")
            return False
            
        if self.token_expiry and self.token_expiry < datetime.utcnow():
            # Only consider it expired if we don't have a refresh token
            if not self.refresh_token:
                logger.warning(f"Token expired for user {self.user_id} and no refresh token")
                return False
                
        return True
