from flask import Blueprint, render_template, redirect, url_for, current_app, request, jsonify, session
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from famos.services.google_tasks import get_user_tasks, update_task, get_tasks_service
from famos.models.integrations import GoogleIntegration
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import traceback
import logging
import sys
import json
from famos import db

# Get a logger for this module
logger = logging.getLogger('famos.routes.main')

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    try:
        logger.debug("=== DASHBOARD ROUTE START ===")
        logger.debug(f"Current user: {current_user}")
        
        # Check if user has Google integration
        integration = GoogleIntegration.query.filter_by(user_id=current_user.id).first()
        logger.info(f"Integration found: {integration is not None}")
        
        google_tasks = []
        task_lists = []
        selected_lists = request.args.getlist('lists') or session.get('selected_lists', [])
        error_message = None
        has_integration = integration is not None
        integration_connected = False
        
        if integration:
            logger.debug("Integration exists, checking status...")
            integration_connected = integration.is_connected()
            logger.debug(f"Integration connected: {integration_connected}")
            logger.debug(f"Access token: {integration.access_token[:10] if integration.access_token else 'None'}...")
            logger.debug(f"Refresh token present: {bool(integration.refresh_token)}")
            logger.debug(f"Token expiry: {integration.token_expiry}")
            logger.debug(f"Tasks enabled: {integration.tasks_enabled}")
            
            if integration_connected and integration.tasks_enabled:  
                logger.debug("Integration is connected and tasks are enabled, fetching tasks...")
                try:
                    # Get task lists before fetching tasks
                    service = get_tasks_service(current_user.id)
                    task_lists_result = service.tasklists().list().execute()
                    task_lists = [{'id': tl['id'], 'title': tl['title']} for tl in task_lists_result.get('items', [])]
                    task_lists.sort(key=lambda x: x['title'])
                    
                    # If no lists selected, default to first list
                    if not selected_lists and task_lists:
                        selected_lists = [task_lists[0]['id']]  # Use ID instead of title
                        session['selected_lists'] = selected_lists
                    
                    # Store selected lists in session
                    session['selected_lists'] = selected_lists
                    
                    # Get all tasks from the service
                    google_tasks = get_user_tasks(current_user.id)
                    
                    # Debug log for task dates
                    for task in google_tasks:
                        logger.debug(f"Task: {task.get('title')}, Due: {task.get('due')}, Raw due: {task.get('raw_due')}")
                    
                    # Filter tasks based on selected lists
                    if selected_lists:
                        google_tasks = [task for task in google_tasks if task.get('list_id') in selected_lists]
                    
                    logger.debug(f"Retrieved {len(google_tasks)} tasks")
                    logger.debug(f"Selected lists: {selected_lists}")
                    
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
                    
                except Exception as e:
                    logger.error(f"Error fetching tasks: {str(e)}")
                    logger.error(traceback.format_exc())
                    error_message = "Error fetching tasks: Please try again later"
            else:
                error_message = "Google Tasks integration is not properly configured"
                
        return render_template(
            'dashboard.html',
            tasks=google_tasks,
            task_lists=task_lists,
            selected_lists=selected_lists,
            error_message=error_message,
            has_integration=has_integration,
            integration_connected=integration_connected
        )
        
    except Exception as e:
        logger.error(f"Error in dashboard route: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('dashboard.html', error_message="An error occurred")
