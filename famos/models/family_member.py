from famos import db
from datetime import datetime

class FamilyMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    relationship = db.Column(db.String(50), nullable=False)
    birthdate = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    family = db.relationship('Family', back_populates='members')
    
    def __repr__(self):
        return f'<FamilyMember {self.first_name} {self.last_name}>'
