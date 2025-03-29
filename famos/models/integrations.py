from famos import db
from datetime import datetime

class GoogleIntegration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(db.String(255), nullable=True)
    refresh_token = db.Column(db.String(255), nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    calendar_enabled = db.Column(db.Boolean, default=False)
    tasks_enabled = db.Column(db.Boolean, default=False)
    docs_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def is_connected(self):
        return bool(self.access_token and self.refresh_token)

    def is_expired(self):
        if not self.token_expiry:
            return True
        return datetime.utcnow() > self.token_expiry
