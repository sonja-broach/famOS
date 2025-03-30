from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from famos.services.google_tasks import get_user_tasks
from famos.models.integrations import GoogleIntegration
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import traceback
import logging
import sys
import json
from famos import db

# Get a logger for this module
logger = logging.getLogger('famos.routes.dashboard')

bp = Blueprint('dashboard', __name__)

@bp.route('/test')
def test():
    logger.debug("Test route hit!")
    return "Test route works!"

@bp.route('/tasks-dashboard')
@login_required
def dashboard():
    try:
        logger.debug("=== DASHBOARD ROUTE START (DEBUG) ===")
        logger.info("=== DASHBOARD ROUTE START (INFO) ===")
        logger.error("=== DASHBOARD ROUTE START (ERROR) ===")
        logger.debug(f"Current user: {current_user}")
        logger.debug(f"Current user ID: {current_user.id}")
        logger.debug(f"Current user is authenticated: {current_user.is_authenticated}")
        
        # Check if user has Google integration
        integration = GoogleIntegration.query.filter_by(user_id=current_user.id).first()
        logger.debug(f"Integration query result: {integration}")
        logger.info(f"Integration found: {integration is not None}")
        
        google_tasks = []
        if integration:
            logger.debug("Integration exists, checking status...")
            is_connected = integration.is_connected()
            logger.debug(f"Integration connected: {is_connected}")
            logger.debug(f"Access token: {integration.access_token[:10] if integration.access_token else 'None'}...")
            logger.debug(f"Refresh token present: {bool(integration.refresh_token)}")
            logger.debug(f"Token expiry: {integration.token_expiry}")
            logger.debug(f"Tasks enabled: {integration.tasks_enabled}")
            
            if is_connected and integration.tasks_enabled:  
                logger.debug("Integration is connected and tasks are enabled, fetching tasks...")
                try:
                    # Create credentials to test if they're valid
                    creds = Credentials(
                        token=integration.access_token,
                        refresh_token=integration.refresh_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=current_app.config['GOOGLE_CLIENT_ID'],
                        client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
                        scopes=['https://www.googleapis.com/auth/tasks.readonly']
                    )
                    
                    # Try to refresh token if needed
                    if creds.expired:
                        logger.debug("Access token expired, attempting refresh...")
                        creds.refresh(Request())
                        integration.access_token = creds.token
                        integration.token_expiry = creds.expiry
                        db.session.commit()
                        logger.debug("Access token refreshed successfully")
                    
                    # Now try to fetch tasks
                    logger.debug("About to call get_user_tasks...")
                    google_tasks = get_user_tasks(current_user.id)  
                    logger.debug(f"Retrieved {len(google_tasks)} tasks")
                    
                    # Add validation of task format
                    validated_tasks = []
                    for task in google_tasks:
                        if not isinstance(task, dict):
                            logger.error(f"Task is not a dictionary: {task}")
                            continue
                        if 'title' not in task:
                            logger.error(f"Task missing title: {task}")
                            continue
                        if not task.get('title'):
                            logger.error(f"Task has empty title: {task}")
                            continue
                        validated_tasks.append(task)
                    google_tasks = validated_tasks
                    
                except ValueError as e:
                    logger.error(f"Invalid integration state: {str(e)}")
                    logger.error(traceback.format_exc())
                except Exception as e:
                    logger.error(f"Error fetching tasks: {str(e)}")
                    logger.error(traceback.format_exc())
            else:
                if not is_connected:
                    logger.debug("Integration exists but is not connected")
                if not integration.tasks_enabled:
                    logger.debug("Tasks are not enabled for this integration")
        else:
            logger.debug("No Google integration found for user")
            
        logger.debug("=== DASHBOARD ROUTE END ===")
        
        return render_template('dashboard.html',
                             google_tasks=google_tasks)
                             
    except Exception as e:
        logger.error(f"Error in dashboard route: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('dashboard.html',
                             google_tasks=[])
