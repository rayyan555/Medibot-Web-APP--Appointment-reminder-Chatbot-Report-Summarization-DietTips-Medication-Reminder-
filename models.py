from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    dob = db.Column(db.Date, nullable=True)
    disease = db.Column(db.String(100), nullable=True)
    caretaker_name = db.Column(db.String(100), nullable=True)
    caretaker_phone = db.Column(db.String(20), nullable=True)

    reminders = db.relationship('Reminder', backref='user', lazy=True)




class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    @property
    def datetime(self):
        """Combine date and time into a single datetime object."""
        return datetime.combine(self.date, self.time)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
