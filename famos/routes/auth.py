from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from datetime import datetime, timezone
import traceback
from famos import db
from famos.models import User, GoogleIntegration, Family
from famos.forms import LoginForm, RegistrationForm
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from pytz import UTC
import os

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
            # Check if email already exists
            if User.query.filter_by(email=form.email.data).first():
                flash('Email already registered. Please use a different one.', 'danger')
                return redirect(url_for('auth.register'))
            
            user = User(
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()  # Flush to get the user ID
            
            # Create default family for the user
            family = Family(
                user_id=user.id,
                name=f"{user.last_name} Family"
            )
            db.session.add(family)
            db.session.commit()
            
            current_app.logger.info(f'New user registered: {user.email} with family: {family.name}')
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f'Error during registration: {str(e)}')
            current_app.logger.error(traceback.format_exc())
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('auth.register'))
    
    return render_template('auth/register.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    current_app.logger.info(f'User {current_user.email} logged out')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/google/auth')
@login_required
def google_auth():
    """Start the Google OAuth flow."""
    try:
        # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                    "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [url_for('auth.google_callback', _external=True)]
                }
            },
            scopes=current_app.config['GOOGLE_AUTH_SCOPES']
        )
        
        # Generate URL for request to Google's OAuth 2.0 server
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        # Store the state in the session
        session['state'] = state
        
        return redirect(authorization_url)
        
    except Exception as e:
        current_app.logger.error(f'Error starting Google OAuth flow: {str(e)}')
        current_app.logger.error(traceback.format_exc())
        flash('Error connecting to Google. Please try again.', 'danger')
        return redirect(url_for('main.dashboard'))

@bp.route('/google/callback')
@login_required
def google_callback():
    """Handle the callback from Google's OAuth 2.0 server."""
    try:
        # Verify state matches
        state = session.get('state')
        if not state or state != request.args.get('state'):
            raise ValueError("State mismatch")
        
        # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                    "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [url_for('auth.google_callback', _external=True)]
                }
            },
            scopes=current_app.config['GOOGLE_AUTH_SCOPES'],
            state=state
        )
        
        # Use the authorization server's response to fetch the OAuth 2.0 tokens
        flow.fetch_token(authorization_response=request.url)
        
        # Get credentials from flow
        credentials = flow.credentials
        
        # Update or create Google integration for user
        integration = GoogleIntegration.query.filter_by(user_id=current_user.id).first()
        if not integration:
            integration = GoogleIntegration(user_id=current_user.id)
        
        integration.access_token = credentials.token
        integration.refresh_token = credentials.refresh_token
        # Store token expiry with timezone info
        integration.token_expiry = credentials.expiry.astimezone(UTC).replace(microsecond=0).isoformat()
        integration.tasks_enabled = True
        
        db.session.add(integration)
        db.session.commit()
        
        current_app.logger.info(f'Successfully connected Google account for user {current_user.email}')
        flash('Successfully connected Google account!', 'success')
        
    except Exception as e:
        current_app.logger.error(f'Error in Google OAuth callback: {str(e)}')
        current_app.logger.error(traceback.format_exc())
        flash('Error connecting Google account. Please try again.', 'danger')
    
    return redirect(url_for('main.dashboard'))
