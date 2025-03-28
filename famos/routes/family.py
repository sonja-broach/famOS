from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('family', __name__, url_prefix='/family')

@bp.route('/')
@login_required
def index():
    return render_template('family/index.html')

@bp.route('/manage')
@login_required
def manage():
    return render_template('family/manage.html')
