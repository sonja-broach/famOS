from famos import db
from datetime import datetime

class Family(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    members = db.relationship('User', back_populates='family')
    tasks = db.relationship('Task', back_populates='family', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Family {self.name}>'
