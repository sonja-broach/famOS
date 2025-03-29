from flask import Blueprint, render_template, redirect, url_for, session, request, flash, current_app
from flask_login import login_required, current_user
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import json
from famos import db
from famos.models.integrations import GoogleIntegration
from famos.config.google import (
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, GOOGLE_SCOPES
)
from famos.utils.logger import logger

bp = Blueprint('integrations', __name__, url_prefix='/account/integrations')

def create_flow():
    """Create OAuth flow with the configured credentials."""
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
            "javascript_origins": ["http://127.0.0.1:5000"]
        }
    }
    logger.info(f"Creating OAuth flow with config: {json.dumps({**client_config['web'], 'client_secret': '[REDACTED]'})}")
    
    flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPES)
    flow.redirect_uri = url_for('integrations.google_callback', _external=True)
    logger.info(f"OAuth flow created successfully with redirect URI: {flow.redirect_uri}")
    return flow

@bp.route('/google')
@login_required
def google_settings():
    try:
        integration = GoogleIntegration.query.filter_by(user_id=current_user.id).first()
        logger.info(f"Fetched Google integration status for user {current_user.id}: {'Connected' if integration and integration.is_connected() else 'Not connected'}")
        return render_template('account/integrations/google.html', integration=integration)
    except Exception as e:
        logger.error(f"Error accessing Google settings: {str(e)}", exc_info=True)
        flash("An error occurred while loading Google integration settings.", "error")
        return redirect(url_for('account.settings'))

@bp.route('/google/connect')
@login_required
def google_connect():
    try:
        flow = create_flow()
        state = request.args.get('state', '')
        logger.info(f"Initiating Google OAuth flow for user {current_user.id} with state: {state}")
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        session['google_oauth_state'] = state
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"Error initiating Google OAuth flow: {str(e)}", exc_info=True)
        flash("Failed to initiate Google connection. Please try again.", "error")
        return redirect(url_for('integrations.google_settings'))

@bp.route('/google/callback')
@login_required
def google_callback():
    try:
        state = session.get('google_oauth_state')
        if not state:
            logger.error(f"OAuth state not found in session for user {current_user.id}")
            raise ValueError("OAuth state not found in session")

        logger.info(f"Processing OAuth callback for user {current_user.id}")
        logger.debug(f"Callback URL: {request.url}")
        
        flow = create_flow()
        # Disable scope validation
        flow.oauth2session._client.scope_checker = lambda *args, **kwargs: None
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        logger.info(f"Successfully obtained OAuth credentials for user {current_user.id}")
        
        # Save or update the integration
        integration = GoogleIntegration.query.filter_by(user_id=current_user.id).first()
        if not integration:
            integration = GoogleIntegration(user_id=current_user.id)
            db.session.add(integration)
            logger.info(f"Creating new Google integration for user {current_user.id}")
        else:
            logger.info(f"Updating existing Google integration for user {current_user.id}")

        integration.access_token = credentials.token
        integration.refresh_token = credentials.refresh_token
        integration.token_uri = credentials.token_uri
        integration.token_expiry = datetime.utcnow() + timedelta(seconds=credentials.expiry.timestamp() - datetime.now().timestamp())
        
        db.session.commit()
        logger.info(f"Successfully saved Google integration for user {current_user.id}")
        flash("Successfully connected to Google!", "success")
        return redirect(url_for('integrations.google_settings'))
    except Exception as e:
        logger.error(f"Error in Google OAuth callback: {str(e)}", exc_info=True)
        flash("Failed to connect to Google. Please try again.", "error")
        return redirect(url_for('integrations.google_settings'))

@bp.route('/google/disconnect')
@login_required
def google_disconnect():
    try:
        integration = GoogleIntegration.query.filter_by(user_id=current_user.id).first()
        if integration:
            logger.info(f"Disconnecting Google integration for user {current_user.id}")
            integration.access_token = None
            integration.refresh_token = None
            integration.token_expiry = None
            integration.calendar_enabled = False
            integration.tasks_enabled = False
            integration.docs_enabled = False
            db.session.commit()
            flash("Successfully disconnected from Google.", "success")
        else:
            logger.info(f"No Google integration found for user {current_user.id} during disconnect attempt")
            flash("No Google integration found.", "info")
    except Exception as e:
        logger.error(f"Error disconnecting Google integration: {str(e)}", exc_info=True)
        flash("Failed to disconnect from Google. Please try again.", "error")
    
    return redirect(url_for('integrations.google_settings'))

@bp.route('/google/update', methods=['POST'])
@login_required
def google_update():
    try:
        integration = GoogleIntegration.query.filter_by(user_id=current_user.id).first()
        if not integration:
            logger.warning(f"Update attempted for non-existent Google integration for user {current_user.id}")
            flash("No Google integration found.", "error")
            return redirect(url_for('integrations.google_settings'))

        if not integration.is_connected():
            logger.warning(f"Update attempted for disconnected Google integration for user {current_user.id}")
            flash("Please connect to Google first.", "error")
            return redirect(url_for('integrations.google_settings'))

        logger.info(f"Updating Google integration settings for user {current_user.id}")
        integration.calendar_enabled = 'calendar' in request.form
        integration.tasks_enabled = 'tasks' in request.form
        integration.docs_enabled = 'docs' in request.form
        
        db.session.commit()
        logger.info(f"Successfully updated Google integration settings for user {current_user.id}")
        flash("Integration settings updated successfully!", "success")
    except Exception as e:
        logger.error(f"Error updating Google integration settings: {str(e)}", exc_info=True)
        flash("Failed to update integration settings. Please try again.", "error")
    
    return redirect(url_for('integrations.google_settings'))
