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

@bp.route('/tasks/update', methods=['POST'])
@login_required
def update_task_route():
    try:
        data = request.json
        task_list_id = data.get('task_list_id')
        task_id = data.get('task_id')
        updates = {
            'status': data.get('status'),
            'notes': data.get('notes'),
            'due': data.get('due')
        }
        
        # Remove None values
        updates = {k: v for k, v in updates.items() if v is not None}
        
        if not task_list_id or not task_id:
            return jsonify({'error': 'Missing task_list_id or task_id'}), 400
            
        updated_task = update_task(current_user.id, task_list_id, task_id, updates)
        return jsonify(updated_task)
        
    except Exception as e:
        logger.error(f"Error updating task: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

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
                        scopes=['https://www.googleapis.com/auth/tasks']
                    )
                    
                    # Try to refresh token if needed
                    if creds.expired:
                        logger.debug("Access token expired, attempting refresh...")
                        creds.refresh(Request())
                        integration.access_token = creds.token
                        integration.token_expiry = creds.expiry
                        db.session.commit()
                        logger.debug("Access token refreshed successfully")
                    
                    # Get task lists before fetching tasks
                    service = get_tasks_service(current_user.id)
                    task_lists_result = service.tasklists().list().execute()
                    task_lists = [{'id': tl['id'], 'title': tl['title']} for tl in task_lists_result.get('items', [])]
                    task_lists.sort(key=lambda x: x['title'])
                    
                    # If no lists selected, default to first list
                    if not selected_lists and task_lists:
                        selected_lists = [task_lists[0]['title']]
                        session['selected_lists'] = selected_lists
                    
                    # Store selected lists in session
                    session['selected_lists'] = selected_lists
                    
                    # Now fetch tasks only for selected lists
                    google_tasks = []
                    for task_list in task_lists:
                        if task_list['title'] in selected_lists:
                            list_tasks = service.tasks().list(tasklist=task_list['id']).execute()
                            for task in list_tasks.get('items', []):
                                google_tasks.append({
                                    'id': task['id'],
                                    'title': task['title'],
                                    'status': task['status'],
                                    'list_id': task_list['id'],
                                    'list_name': task_list['title'],
                                    'notes': task.get('notes', ''),
                                    'due': task.get('due', ''),
                                    'completed': task.get('completed', ''),
                                    'parent': task.get('parent', '')
                                })
                    
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
        
        # Generate CSRF token for AJAX requests
        csrf_token = generate_csrf()
        
        return render_template('dashboard.html',
                             google_tasks=google_tasks,
                             task_lists=task_lists,
                             selected_lists=selected_lists,
                             csrf_token=csrf_token)

    except Exception as e:
        logger.error(f"Error in dashboard route: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('dashboard.html', google_tasks=[], task_lists=[], selected_lists=[])
