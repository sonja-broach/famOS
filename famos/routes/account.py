from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

bp = Blueprint('account', __name__, url_prefix='/account')

@bp.route('/settings')
@login_required
def settings():
    return render_template('account/settings.html')
