from famos import db
import json
from datetime import datetime

class GoogleIntegration(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    access_token = db.Column(db.String(255))
    refresh_token = db.Column(db.String(255))
    token_uri = db.Column(db.String(255))
    token_expiry = db.Column(db.DateTime)
    calendar_enabled = db.Column(db.Boolean, default=False)
    tasks_enabled = db.Column(db.Boolean, default=False)
    docs_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def is_connected(self):
        return bool(self.access_token and self.refresh_token)
