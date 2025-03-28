from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from famos import db
from famos.models import User
from famos.forms import LoginForm, RegistrationForm

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        current_app.logger.info(f'Already authenticated user {current_user.email} redirected to dashboard')
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            current_app.logger.warning(f'Failed login attempt for email: {form.email.data}')
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))
        
        # Log out any existing session before logging in
        if current_user.is_authenticated:
            logout_user()
            
        login_user(user, remember=form.remember.data)
        current_app.logger.info(f'Successful login for user: {user.email}')
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.dashboard')
        flash('Welcome back!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        current_app.logger.info(f'Already authenticated user {current_user.email} redirected to dashboard')
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            
            current_app.logger.info(f'New user registered: {user.email}')
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            current_app.logger.error(f'Error during registration for email {form.email.data}: {str(e)}')
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('auth.register'))
    
    return render_template('auth/register.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    email = current_user.email
    logout_user()
    current_app.logger.info(f'User logged out: {email}')
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))
