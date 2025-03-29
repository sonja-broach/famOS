from flask import Blueprint, render_template
from flask_login import login_required, current_user
from famos.services.google_tasks import get_user_tasks

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
def dashboard():
    # Fetch Google Tasks if the user has connected their account
    google_tasks = get_user_tasks(current_user.id)
    
    return render_template('dashboard/index.html',
                         google_tasks=google_tasks)
