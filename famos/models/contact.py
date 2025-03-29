from famos import db
from datetime import datetime

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(50), nullable=False)  # e.g., babysitter, doctor, etc.
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign key to Family
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=False)
    family = db.relationship('Family', back_populates='contacts')

    def __repr__(self):
        return f'<Contact {self.first_name} {self.last_name}>'
