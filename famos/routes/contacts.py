from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from famos import db
from famos.models.contact import Contact
from famos.forms.family import ContactForm
from famos.utils.logger import logger
from sqlalchemy.exc import SQLAlchemyError

bp = Blueprint('contacts', __name__, url_prefix='/contacts')

@bp.route('/', methods=['GET'])
@login_required
def index():
    form = ContactForm()
    if not current_user.family:
        flash('You need to create or join a family first.', 'error')
        return redirect(url_for('family.create'))
    
    try:
        contacts = Contact.query.filter_by(family_id=current_user.family_id).all()
    except SQLAlchemyError as e:
        logger.error(f'Database error while fetching contacts: {str(e)}')
        flash('An error occurred while loading contacts.', 'error')
        contacts = []
    
    return render_template('contacts/index.html', form=form, contacts=contacts)

@bp.route('/add', methods=['POST'])
@login_required
def add_contact():
    if not current_user.family:
        flash('You need to create or join a family first.', 'error')
        return redirect(url_for('family.create'))
    
    form = ContactForm()
    if form.validate_on_submit():
        try:
            contact = Contact(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data,
                phone=form.phone.data,
                role=form.role.data,
                notes=form.notes.data,
                family_id=current_user.family_id
            )
            db.session.add(contact)
            db.session.commit()
            flash('Contact added successfully!', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f'Error adding contact: {str(e)}')
            flash('An error occurred while adding the contact.', 'error')
    
    return redirect(url_for('contacts.index'))

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_contact(id):
    contact = Contact.query.get_or_404(id)
    if contact.family_id != current_user.family_id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('contacts.index'))
    
    form = ContactForm(obj=contact)
    if form.validate_on_submit():
        try:
            contact.first_name = form.first_name.data
            contact.last_name = form.last_name.data
            contact.email = form.email.data
            contact.phone = form.phone.data
            contact.role = form.role.data
            contact.notes = form.notes.data
            db.session.commit()
            flash('Contact updated successfully!', 'success')
            return redirect(url_for('contacts.index'))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f'Error updating contact: {str(e)}')
            flash('An error occurred while updating the contact.', 'error')
    
    return render_template('contacts/edit.html', form=form, contact=contact)
