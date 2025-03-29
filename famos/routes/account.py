from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from famos import db
from famos.forms.account import AccountSettingsForm
from famos.utils.logger import logger
from sqlalchemy.exc import SQLAlchemyError

bp = Blueprint('account', __name__, url_prefix='/account')

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    try:
        form = AccountSettingsForm()
        if request.method == 'GET':
            # Pre-populate form with current user data
            form.first_name.data = current_user.first_name
            form.last_name.data = current_user.last_name
            form.email.data = current_user.email
            form.phone.data = current_user.phone
            return render_template('account/settings.html', form=form)
        
        if form.validate_on_submit():
            try:
                # Verify current password if trying to change password
                if form.new_password.data:
                    if not form.current_password.data:
                        flash('Current password is required to set a new password.', 'error')
                        return render_template('account/settings.html', form=form)
                    
                    if not check_password_hash(current_user.password_hash, form.current_password.data):
                        flash('Current password is incorrect.', 'error')
                        return render_template('account/settings.html', form=form)
                    
                    current_user.password_hash = generate_password_hash(form.new_password.data)
                
                # Update other fields
                current_user.first_name = form.first_name.data
                current_user.last_name = form.last_name.data
                current_user.email = form.email.data
                current_user.phone = form.phone.data
                
                db.session.commit()
                flash('Account settings updated successfully!', 'success')
                return redirect(url_for('main.dashboard'))
                
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f'Error updating account settings: {str(e)}')
                flash('A database error occurred while updating your account settings. Please try again.', 'error')
                return render_template('account/settings.html', form=form)
        
        return render_template('account/settings.html', form=form)
    except Exception as e:
        logger.error(f'Error in account settings: {str(e)}')
        flash('We encountered a technical issue while accessing your account settings. Our team has been notified. Please try again or contact support if the issue persists.', 'error')
        return redirect(url_for('main.dashboard'))
