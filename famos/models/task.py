from famos import db
from datetime import datetime

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    priority = db.Column(db.Integer, default=1)  # 1=Low, 2=Medium, 3=High
    
    # Relationships
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=False)
    family = db.relationship('Family', back_populates='tasks')
    
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assignee = db.relationship('User', back_populates='assigned_tasks')
    
    def complete(self):
        self.completed = True
        self.completed_at = datetime.utcnow()
        
    def __repr__(self):
        return f'<Task {self.title}>'
