from famos import db
from datetime import datetime
import logging
from datetime import timezone as tz

# Get a logger for this module
logger = logging.getLogger(__name__)

class GoogleIntegration(db.Model):
    """Model for storing Google integration settings."""
    __tablename__ = 'google_integrations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(db.String(255), nullable=True)  
    refresh_token = db.Column(db.String(255), nullable=True)
    token_uri = db.Column(db.String, nullable=True)
    token_expiry = db.Column(db.String(32), nullable=True)  
    calendar_enabled = db.Column(db.Boolean, default=False)
    tasks_enabled = db.Column(db.Boolean, default=False)
    docs_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(tz.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(tz.utc), onupdate=datetime.now(tz.utc))
    
    # Relationships
    user = db.relationship('User', back_populates='google_integration')

    def is_connected(self):
        """Check if the integration is connected and valid."""
        logger.info(f"Checking connection status for user {self.user_id}")
        logger.info(f"Access token: {'Present' if self.access_token else 'Missing'}")
        logger.info(f"Refresh token: {'Present' if self.refresh_token else 'Missing'}")
        logger.info(f"Token expiry: {self.token_expiry}")
        
        if not self.access_token:
            logger.warning(f"No access token for user {self.user_id}")
            return False
            
        if self.token_expiry:
            try:
                # Parse the ISO format string with timezone info
                expiry = datetime.fromisoformat(self.token_expiry)
                if not expiry.tzinfo:
                    # If no timezone info, assume UTC
                    expiry = expiry.replace(tzinfo=tz.utc)
                if expiry < datetime.now(tz.utc):
                    # Only consider it expired if we don't have a refresh token
                    if not self.refresh_token:
                        logger.warning(f"Token expired for user {self.user_id} and no refresh token")
                        return False
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid token expiry format for user {self.user_id}: {self.token_expiry}")
                return False
                
        return True
