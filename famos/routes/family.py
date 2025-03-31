from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from famos import db
from famos.models.family import Family
from famos.models.user import User
from famos.models.contact import Contact
from famos.forms.family import FamilyMemberForm, CreateFamilyForm
from famos.utils.logger import logger
from sqlalchemy.exc import SQLAlchemyError

bp = Blueprint('family', __name__, url_prefix='/family')

@bp.route('/')
@login_required
def index():
    if not current_user.family:
        return redirect(url_for('family.create'))
    return render_template('family/index.html')

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if current_user.family:
        flash('You already have a family.', 'info')
        return redirect(url_for('family.manage'))
    
    form = CreateFamilyForm()
    if form.validate_on_submit():
        try:
            family = Family(name=form.name.data)
            db.session.add(family)
            current_user.family = family
            db.session.commit()
            flash('Family created successfully!', 'success')
            return redirect(url_for('family.manage'))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f'Error creating family: {str(e)}')
            flash('An error occurred while creating your family.', 'error')
    
    return render_template('family/create.html', form=form)

@bp.route('/manage', methods=['GET', 'POST'])
@login_required
def manage():
    member_form = FamilyMemberForm()
    family = current_user.family
    
    if not family:
        logger.error(f'User {current_user.email} attempted to access family management without a family')
        flash('You need to create or join a family first.', 'error')
        return redirect(url_for('family.create'))
    
    try:
        members = User.query.join(Family).filter(Family.id == family.id).all()
    except SQLAlchemyError as e:
        logger.error(f'Database error while fetching family members: {str(e)}')
        flash('An error occurred while loading family members.', 'error')
        members = []
    
    if request.method == 'POST' and member_form.validate_on_submit():
        try:
            new_member = User(
                first_name=member_form.first_name.data,
                last_name=member_form.last_name.data,
                email=member_form.email.data,
                phone=member_form.phone.data,
                family=family
            )
            db.session.add(new_member)
            db.session.commit()
            logger.info(f'New family member added: {new_member.email}')
            flash('Family member added successfully!', 'success')
            return redirect(url_for('family.manage'))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f'Error adding family member: {str(e)}')
            flash('An error occurred while adding the family member.', 'error')
    
    return render_template('family/manage.html', form=member_form, members=members)

@bp.route('/member/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_member(id):
    member = User.query.get_or_404(id)
    if not current_user.family or member.family.id != current_user.family.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('family.manage'))
    
    form = FamilyMemberForm(obj=member)
    if form.validate_on_submit():
        try:
            member.first_name = form.first_name.data
            member.last_name = form.last_name.data
            member.email = form.email.data
            member.phone = form.phone.data
            db.session.commit()
            flash('Family member updated successfully!', 'success')
            return redirect(url_for('family.manage'))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f'Error updating family member: {str(e)}')
            flash('An error occurred while updating the family member.', 'error')
    
    return render_template('family/edit_member.html', form=form, member=member)

# Removed duplicate contacts routes since they're now in contacts.py
