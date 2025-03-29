from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, TelField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Optional, Length

class CreateFamilyForm(FlaskForm):
    name = StringField('Family Name', validators=[DataRequired(), Length(max=100)])

class FamilyMemberForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = EmailField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone = TelField('Phone', validators=[Optional(), Length(max=20)])

class ContactForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = EmailField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = TelField('Phone', validators=[Optional(), Length(max=20)])
    role = SelectField('Role', choices=[
        ('babysitter', 'Babysitter'),
        ('doctor', 'Doctor'),
        ('teacher', 'Teacher'),
        ('relative', 'Relative'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
