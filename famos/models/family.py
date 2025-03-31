from famos import db
from datetime import datetime

class Family(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='family')
    tasks = db.relationship('Task', back_populates='family', cascade='all, delete-orphan')
    contacts = db.relationship('Contact', back_populates='family', cascade='all, delete-orphan')
    members = db.relationship('FamilyMember', back_populates='family', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Family {self.name}>'
