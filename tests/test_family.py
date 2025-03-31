import pytest
from unittest.mock import patch, MagicMock
from famos.models.user import User
from famos.models.family import Family
from famos.models.family_member import FamilyMember
from famos.models import Contact
from famos import db
from datetime import datetime, timezone
from flask_login import login_user as flask_login_user

def test_add_family_member(auth_client, authenticated_user):
    """Test adding a family member."""
    with auth_client.application.app_context():
        # Create family for user if not exists
        if not authenticated_user.family:
            family = Family(
                name='Test Family',
                user_id=authenticated_user.id
            )
            authenticated_user.family = family
            db.session.add(family)
            db.session.add(authenticated_user)
            db.session.commit()
            db.session.refresh(authenticated_user)
        
        data = {
            'first_name': 'Test',
            'last_name': 'Member',
            'relationship': 'Child',
            'birthdate': '2020-01-01'
        }
        
        response = auth_client.post('/family/members/add', data=data)
        assert response.status_code == 302  # Redirects after successful addition
        
        # Refresh the session to get updated data
        db.session.refresh(authenticated_user)
        family = authenticated_user.family
        assert family is not None
        assert len(family.members) == 1
        member = family.members[0]
        assert member.first_name == 'Test'
        assert member.last_name == 'Member'
        assert member.relationship == 'Child'

def test_edit_family_member(auth_client, authenticated_user):
    """Test editing a family member."""
    with auth_client.application.app_context():
        # Create family if not exists
        if not authenticated_user.family:
            family = Family(
                name='Test Family',
                user_id=authenticated_user.id
            )
            authenticated_user.family = family
            db.session.add(family)
            db.session.add(authenticated_user)
            db.session.commit()
            db.session.refresh(authenticated_user)
        
        # Create member
        member = FamilyMember(
            family_id=authenticated_user.family.id,
            first_name='Test',
            last_name='Member',
            relationship='Child',
            birthdate=datetime.now(timezone.utc)
        )
        db.session.add(member)
        db.session.commit()
        db.session.refresh(member)
        
        # Edit member
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'relationship': 'Sibling',
            'birthdate': '2019-01-01'
        }
        
        response = auth_client.post(f'/family/members/{member.id}/edit', data=data)
        assert response.status_code == 302
        
        # Refresh session to get updated data
        db.session.refresh(member)
        assert member.first_name == 'Updated'
        assert member.last_name == 'Name'
        assert member.relationship == 'Sibling'

def test_unauthorized_member_edit(auth_client, authenticated_user):
    """Test that users cannot edit family members they don't own."""
    with auth_client.application.app_context():
        # Create another user and their family member
        other_user = User(email='other@example.com', first_name='Other', last_name='User')
        other_user.set_password('password')
        db.session.add(other_user)
        db.session.commit()
        
        other_family = Family(
            name='Other Family',
            user_id=other_user.id
        )
        other_user.family = other_family
        db.session.add(other_family)
        db.session.add(other_user)
        db.session.commit()
        db.session.refresh(other_user)
        
        member = FamilyMember(
            family_id=other_family.id,
            first_name='Test',
            last_name='Member',
            relationship='Child',
            birthdate=datetime.now(timezone.utc)
        )
        db.session.add(member)
        db.session.commit()
        db.session.refresh(member)
        
        # Try to edit the other user's family member
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'relationship': 'Sibling',
            'birthdate': '2019-01-01'
        }
        
        response = auth_client.post(f'/family/members/{member.id}/edit', data=data)
        assert response.status_code == 403  # Forbidden

def test_add_contact(auth_client, authenticated_user):
    """Test adding a contact."""
    with auth_client.application.app_context():
        # Create family for user if not exists
        if not authenticated_user.family:
            family = Family(
                name='Test Family',
                user_id=authenticated_user.id
            )
            authenticated_user.family = family
            db.session.add(family)
            db.session.add(authenticated_user)
            db.session.commit()
            db.session.refresh(authenticated_user)
        
        data = {
            'first_name': 'Test',
            'last_name': 'Contact',
            'email': 'test@contact.com',
            'phone': '1234567890',
            'role': 'Friend'  # Changed from relationship to role
        }
        
        response = auth_client.post('/family/contacts/add', data=data)
        assert response.status_code == 302  # Redirects after successful addition
        
        # Refresh the session to get updated data
        db.session.refresh(authenticated_user)
        family = authenticated_user.family
        assert family is not None
        assert len(family.contacts) == 1
        contact = family.contacts[0]
        assert contact.first_name == 'Test'
        assert contact.last_name == 'Contact'
        assert contact.email == 'test@contact.com'

def test_edit_contact(auth_client, authenticated_user):
    """Test editing a contact."""
    with auth_client.application.app_context():
        # Create family if not exists
        if not authenticated_user.family:
            family = Family(
                name='Test Family',
                user_id=authenticated_user.id
            )
            authenticated_user.family = family
            db.session.add(family)
            db.session.add(authenticated_user)
            db.session.commit()
            db.session.refresh(authenticated_user)
        
        # Create contact
        contact = Contact(
            family_id=authenticated_user.family.id,
            first_name='Test',
            last_name='Contact',
            email='test@contact.com',
            phone='1234567890',
            role='Friend'  # Changed from relationship to role
        )
        db.session.add(contact)
        db.session.commit()
        db.session.refresh(contact)
        
        # Edit contact
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@contact.com',
            'phone': '0987654321',
            'role': 'Family Friend'  # Changed from relationship to role
        }
        
        response = auth_client.post(f'/family/contacts/{contact.id}/edit', data=data)
        assert response.status_code == 302
        
        # Refresh session to get updated data
        db.session.refresh(contact)
        assert contact.first_name == 'Updated'
        assert contact.last_name == 'Name'
        assert contact.email == 'updated@contact.com'

def test_unauthorized_contact_edit(auth_client, authenticated_user):
    """Test that users cannot edit contacts they don't own."""
    with auth_client.application.app_context():
        # Create another user and their contact
        other_user = User(email='other@example.com', first_name='Other', last_name='User')
        other_user.set_password('password')
        db.session.add(other_user)
        db.session.commit()
        
        other_family = Family(
            name='Other Family',
            user_id=other_user.id
        )
        other_user.family = other_family
        db.session.add(other_family)
        db.session.add(other_user)
        db.session.commit()
        db.session.refresh(other_user)
        
        contact = Contact(
            family_id=other_family.id,
            first_name='Test',
            last_name='Contact',
            email='test@contact.com',
            phone='1234567890',
            role='Friend'  # Changed from relationship to role
        )
        db.session.add(contact)
        db.session.commit()
        db.session.refresh(contact)
        
        # Try to edit the other user's contact
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@contact.com',
            'phone': '0987654321',
            'role': 'Family Friend'  # Changed from relationship to role
        }
        
        response = auth_client.post(f'/family/contacts/{contact.id}/edit', data=data)
        assert response.status_code == 403  # Forbidden

def test_access_without_family(auth_client, authenticated_user):
    """Test accessing family pages without a family record."""
    with auth_client.application.app_context():
        # Delete any existing family record
        if authenticated_user.family:
            db.session.delete(authenticated_user.family)
            db.session.commit()
            db.session.refresh(authenticated_user)
    
    response = auth_client.get('/family')
    assert response.status_code == 302  # Should redirect to family setup
    assert '/family/setup' in response.headers['Location']
