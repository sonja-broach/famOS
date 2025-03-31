from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from flask import current_app
from famos.models.integrations import GoogleIntegration
from datetime import datetime, timedelta, timezone
import json
import os
import logging
import sys
import traceback
from google.auth.transport.requests import Request
from famos.extensions import db

# Get a logger for this module
logger = logging.getLogger('famos.services.google_tasks')

def get_tasks_service(user_id):
    """Get a Google Tasks service instance for the given user."""
    logger.info(f"=== Getting tasks service for user {user_id} ===")
    
    integration = GoogleIntegration.query.filter_by(user_id=user_id).first()
    if not integration:
        logger.error(f"No integration found for user {user_id}")
        raise ValueError(f"No integration found for user {user_id}")
    
    if not integration.access_token:
        logger.error(f"No access token for user {user_id}")
        raise ValueError(f"No access token for user {user_id}")
        
    try:
        logger.info(f"Creating credentials with token: {integration.access_token[:10]}...")
        logger.info(f"Refresh token present: {bool(integration.refresh_token)}")
        logger.info(f"Token expiry: {integration.token_expiry}")
        
        # Check if we have all required config
        if not current_app.config.get('GOOGLE_CLIENT_ID'):
            logger.error("Missing GOOGLE_CLIENT_ID in config")
            raise ValueError("Missing GOOGLE_CLIENT_ID in config")
        if not current_app.config.get('GOOGLE_CLIENT_SECRET'):
            logger.error("Missing GOOGLE_CLIENT_SECRET in config")
            raise ValueError("Missing GOOGLE_CLIENT_SECRET in config")
            
        creds = Credentials(
            token=integration.access_token,
            refresh_token=integration.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=current_app.config['GOOGLE_CLIENT_ID'],
            client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
            scopes=['https://www.googleapis.com/auth/tasks']  # Need full access for updates
        )
        
        # Check if credentials need refresh
        if integration.token_expiry:
            expiry = datetime.fromisoformat(integration.token_expiry).replace(tzinfo=timezone.utc)
            if expiry < datetime.now(timezone.utc):
                logger.info(f"Token expired at {expiry}, current time is {datetime.now(timezone.utc)}")
                if not integration.refresh_token:
                    logger.error("No refresh token available")
                    raise ValueError(f"Access token expired and no refresh token available for user {user_id}")
                    
                logger.info("Attempting to refresh token...")
                creds.refresh(Request())
                
                # Update the integration with new tokens
                integration.access_token = creds.token
                integration.token_expiry = creds.expiry.isoformat()
                db.session.commit()
                
                logger.info(f"Token refreshed successfully. New expiry: {integration.token_expiry}")
        
        logger.info("Building tasks service...")
        service = build('tasks', 'v1', credentials=creds)
        logger.info("Tasks service built successfully")
        return service
        
    except Exception as e:
        logger.error(f"Error creating tasks service: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def standardize_date(date_str):
    """Convert any date string to our standard format."""
    if not date_str:
        return ""
        
    logger.debug(f"Standardizing date: {date_str}")
    
    try:
        # Try parsing different formats
        try:
            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            logger.debug(f"Parsed as format 1: %Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
                logger.debug(f"Parsed as format 2: %Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    logger.debug(f"Parsed as format 3: %Y-%m-%d")
                except ValueError:
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
                        logger.debug(f"Parsed as format 4: %Y-%m-%dT%H:%M:%S%z")
                    except ValueError:
                        try:
                            date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                            logger.debug(f"Parsed as format 5: %Y-%m-%d %H:%M:%S")
                        except ValueError:
                            logger.error(f"Could not parse date: {date_str}")
                            return date_str
        
        # Convert to UTC if it has a timezone
        if hasattr(date, 'tzinfo') and date.tzinfo is not None:
            date = date.astimezone(timezone.utc)
        
        # Add time if it's just a date
        if date.hour == 0 and date.minute == 0 and date.second == 0:
            date = date.replace(hour=12, minute=0)
        
        # Convert to standard format
        result = date.strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.debug(f"Standardized date: {result}")
        return result
    except Exception as e:
        logger.error(f"Error standardizing date {date_str}: {str(e)}")
        return date_str

def get_user_tasks(user_id):
    """Fetch all tasks from Google Tasks for the given user."""
    logger.info(f"=== Starting to fetch tasks for user {user_id} ===")
    
    try:
        logger.debug("About to call get_tasks_service...")
        service = get_tasks_service(user_id)
        logger.debug(f"get_tasks_service returned: {service}")
        
        if not service:
            error_msg = f"Could not create tasks service for user {user_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Get all task lists
        logger.info("Fetching task lists...")
        try:
            task_lists_result = service.tasklists().list().execute()
            logger.debug(f"Raw task lists response: {json.dumps(task_lists_result)}")
        except Exception as e:
            logger.error(f"Error fetching task lists: {str(e)}")
            logger.error(traceback.format_exc())
            raise
            
        task_lists = task_lists_result.get('items', [])
        logger.info(f"Found {len(task_lists)} task lists")
        
        all_tasks = []
        
        # Get tasks from each task list
        for task_list in task_lists:
            list_id = task_list['id']
            list_title = task_list['title']
            logger.info(f"Fetching tasks from list: {list_title} (ID: {list_id})")
            
            try:
                # Get tasks from this list
                tasks_result = service.tasks().list(tasklist=list_id).execute()
                logger.debug(f"Raw tasks response for list {list_title}: {json.dumps(tasks_result)}")
                
                tasks = tasks_result.get('items', [])
                logger.info(f"Found {len(tasks)} tasks in list {list_title}")
                
                # Process each task
                for task in tasks:
                    try:
                        task_data = {
                            'task_id': task.get('id', ''),
                            'list_id': list_id,
                            'title': task.get('title', ''),
                            'notes': task.get('notes', ''),
                            'due': standardize_date(task.get('due', '')),
                            'status': task.get('status', ''),
                            'list_name': list_title,
                            'completed': task.get('completed', '')
                        }
                        
                        # Log the raw task data for debugging
                        logger.debug(f"Raw task data: {task}")
                        logger.debug(f"Processed task data: {task_data}")
                        
                        all_tasks.append(task_data)
                        
                    except Exception as e:
                        logger.error(f"Error processing task in list {list_title}: {str(e)}")
                        logger.error(f"Problem task data: {json.dumps(task)}")
                        logger.error(traceback.format_exc())
                        continue
                    
            except Exception as e:
                logger.error(f"Error fetching tasks from list {list_title}: {str(e)}")
                logger.error(traceback.format_exc())
                continue
                
        logger.info(f"=== Finished fetching tasks for user {user_id}. Found {len(all_tasks)} tasks ===")
        return all_tasks
        
    except Exception as e:
        logger.error(f"Error in get_user_tasks: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def update_task(user_id, task_list_id, task_id, updates):
    """Update a task with new information."""
    logger.info(f"=== Updating task {task_id} in list {task_list_id} for user {user_id} ===")
    logger.debug(f"Updates to apply: {json.dumps(updates)}")
    
    try:
        service = get_tasks_service(user_id)
        
        # First get the current task
        task = service.tasks().get(tasklist=task_list_id, task=task_id).execute()
        logger.debug(f"Current task state: {json.dumps(task)}")
        
        # Apply updates
        for key, value in updates.items():
            if value is not None:  # Only update if value is not None
                task[key] = value
        
        # Update the task
        updated_task = service.tasks().update(
            tasklist=task_list_id,
            task=task_id,
            body=task
        ).execute()
        
        logger.info("Task updated successfully")
        logger.debug(f"Updated task: {json.dumps(updated_task)}")
        
        # Return raw task response
        return updated_task
        
    except Exception as e:
        logger.error(f"Error updating task: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def get_task_list_title(user_id, list_id):
    """Get the title of a task list by its ID."""
    service = get_tasks_service(user_id)
    task_list = service.tasklists().get(tasklist=list_id).execute()
    return task_list.get('title', '')
