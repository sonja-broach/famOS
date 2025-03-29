from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from flask import current_app
from famos.models.integrations import GoogleIntegration

def get_tasks_service(user_id):
    """Get a Google Tasks service instance for the given user."""
    integration = GoogleIntegration.query.filter_by(user_id=user_id).first()
    current_app.logger.info(f"Getting tasks service for user {user_id}. Integration found: {integration is not None}")
    
    if not integration or not integration.access_token:
        return None
    
    creds = Credentials(
        token=integration.access_token,
        refresh_token=integration.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=current_app.config['GOOGLE_CLIENT_ID'],
        client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
        scopes=['https://www.googleapis.com/auth/tasks.readonly']
    )
    current_app.logger.info(f"Created credentials for user {user_id}")
    
    return build('tasks', 'v1', credentials=creds)

def get_user_tasks(user_id):
    """Fetch all tasks from Google Tasks for the given user."""
    service = get_tasks_service(user_id)
    if not service:
        current_app.logger.warning(f"No tasks service available for user {user_id}")
        return []
    
    try:
        # Get all task lists
        task_lists_result = service.tasklists().list().execute()
        current_app.logger.info(f"Task lists response: {task_lists_result}")
        task_lists = task_lists_result.get('items', [])
        
        all_tasks = []
        
        # Get tasks from each task list
        for task_list in task_lists:
            current_app.logger.info(f"Fetching tasks for list: {task_list.get('title')}")
            tasks_result = service.tasks().list(tasklist=task_list['id']).execute()
            current_app.logger.info(f"Tasks response for list {task_list.get('title')}: {tasks_result}")
            tasks = tasks_result.get('items', [])
            for task in tasks:
                if task.get('status') != 'completed':  # Only include incomplete tasks
                    all_tasks.append({
                        'title': task.get('title', 'Untitled Task'),
                        'due': task.get('due'),
                        'notes': task.get('notes'),
                        'list_name': task_list.get('title', 'Default List'),
                        'source': 'google',
                        'id': task.get('id'),
                        'list_id': task_list.get('id')
                    })
        
        current_app.logger.info(f"Found {len(all_tasks)} tasks for user {user_id}")
        return all_tasks
    except Exception as e:
        current_app.logger.error(f"Error fetching Google Tasks: {str(e)}")
        return []
