from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('contacts', __name__, url_prefix='/contacts')

@bp.route('/')
@login_required
def index():
    return render_template('contacts/index.html')
