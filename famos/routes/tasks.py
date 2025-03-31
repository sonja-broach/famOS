from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from famos.services.google_tasks import get_tasks_service
from datetime import datetime
import logging

bp = Blueprint('tasks', __name__, url_prefix='/tasks')

@bp.route('/')
@login_required
def index():
    return render_template('tasks/index.html')

@bp.route('/test')
@login_required
def test():
    print("=== Test route called ===")
    return jsonify({'success': True, 'message': 'Tasks blueprint is working'})

@bp.route('/update', methods=['POST'])
@login_required
def update_task():
    try:
        print("=== Starting task update ===")
        data = request.get_json()
        print("Request data:", data)
        if not data:
            print("No JSON data received")
            return jsonify({'success': False, 'error': 'No JSON data received'}), 400
            
        task_id = data.get('task_id')
        task_list_id = data.get('task_list_id')
        print("Task ID:", task_id)
        print("Task List ID:", task_list_id)

        if not task_id or not task_list_id:
            print("Missing task_id or task_list_id")
            return jsonify({'success': False, 'error': 'Missing task_id or task_list_id'}), 400
            
        updates = {}
        
        # Only include fields that are present in the request
        if 'status' in data:
            updates['status'] = data['status']
        if 'notes' in data:
            updates['notes'] = data['notes']
        if 'due' in data and data['due']:
            try:
                # Convert the datetime-local input to RFC 3339 format
                due_date = datetime.fromisoformat(data['due'])
                updates['due'] = due_date.isoformat() + 'Z'
            except ValueError as e:
                print("Error parsing due date:", e)
                return jsonify({'success': False, 'error': f'Invalid date format: {e}'}), 400
        
        print("Updates to apply:", updates)
        
        try:
            print("Getting tasks service...")
            service = get_tasks_service(current_user.id)
            print("Getting current task...")
            task = service.tasks().get(tasklist=task_list_id, task=task_id).execute()
            print("Current task:", task)
            
            # Update task with new values
            task.update(updates)
            print("Task after updates:", task)
            
            # Send update to Google Tasks API
            print("Sending update to Google Tasks API...")
            updated_task = service.tasks().update(
                tasklist=task_list_id,
                task=task_id,
                body=task
            ).execute()
            print("Update successful:", updated_task)
            
            return jsonify({'success': True, 'task': updated_task})
        except Exception as e:
            print("Error updating task:", e)
            logging.error(f"Error updating task: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
            
    except Exception as e:
        print("Unexpected error in update_task:", e)
        logging.error(f"Unexpected error in update_task: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500
