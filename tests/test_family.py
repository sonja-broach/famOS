import pytest
from famos import db
from famos.models.user import User
from famos.models.family import Family
from famos.models.contact import Contact

def test_add_family_member(test_client, session, test_family):
    # Add a new family member
    response = test_client.post('/family/members/add', data={
        'first_name': 'Jane',
        'last_name': 'Doe',
        'email': 'jane@example.com',
        'phone': '123-456-7890',
        'csrf_token': 'test-csrf-token'
    }, follow_redirects=True)
    
    assert b'Family member added successfully!' in response.data
    
    # Verify member was added to database
    member = session.query(User).filter_by(email='jane@example.com').first()
    assert member is not None
    assert member.first_name == 'Jane'
    assert member.last_name == 'Doe'
    assert member.family_id == test_family.id

def test_edit_family_member(test_client, session, test_family):
    # Create a test member
    member = User(
        first_name='Original',
        last_name='Name',
        email='original@example.com',
        phone='111-111-1111',
        family_id=test_family.id,
        password_hash='dummy-hash'
    )
    session.add(member)
    session.commit()
    
    # Edit the member
    response = test_client.post(f'/family/members/{member.id}/edit', data={
        'first_name': 'Updated',
        'last_name': 'Name',
        'email': 'updated@example.com',
        'phone': '222-222-2222',
        'csrf_token': 'test-csrf-token'
    }, follow_redirects=True)
    
    assert b'Family member updated successfully!' in response.data
    
    # Verify changes in database
    session.refresh(member)
    assert member.first_name == 'Updated'
    assert member.email == 'updated@example.com'

def test_unauthorized_member_edit(test_client, session, test_family):
    # Create another family
    other_family = Family(name='Other Family')
    session.add(other_family)
    session.commit()
    
    # Create a member in the other family
    other_member = User(
        first_name='Other',
        last_name='Person',
        email='other@example.com',
        family_id=other_family.id,
        password_hash='dummy-hash'
    )
    session.add(other_member)
    session.commit()
    
    # Try to edit member from other family
    response = test_client.get(f'/family/members/{other_member.id}/edit', follow_redirects=True)
    assert b'Unauthorized access' in response.data

def test_add_contact(test_client, session, test_family):
    # Add a new contact
    response = test_client.post('/family/contacts/add', data={
        'first_name': 'John',
        'last_name': 'Smith',
        'email': 'john@example.com',
        'phone': '333-333-3333',
        'role': 'babysitter',
        'notes': 'Available weekends',
        'csrf_token': 'test-csrf-token'
    }, follow_redirects=True)
    
    assert b'Contact added successfully!' in response.data
    
    # Verify contact was added to database
    contact = session.query(Contact).filter_by(email='john@example.com').first()
    assert contact is not None
    assert contact.first_name == 'John'
    assert contact.role == 'babysitter'
    assert contact.family_id == test_family.id

def test_edit_contact(test_client, session, test_family):
    # Create a test contact
    contact = Contact(
        first_name='Original',
        last_name='Contact',
        email='contact@example.com',
        phone='444-444-4444',
        role='teacher',
        notes='Original notes',
        family_id=test_family.id
    )
    session.add(contact)
    session.commit()
    
    # Edit the contact
    response = test_client.post(f'/family/contacts/{contact.id}/edit', data={
        'first_name': 'Updated',
        'last_name': 'Contact',
        'email': 'updated@example.com',
        'phone': '555-555-5555',
        'role': 'doctor',
        'notes': 'Updated notes',
        'csrf_token': 'test-csrf-token'
    }, follow_redirects=True)
    
    assert b'Contact updated successfully!' in response.data
    
    # Verify changes in database
    session.refresh(contact)
    assert contact.first_name == 'Updated'
    assert contact.role == 'doctor'
    assert contact.notes == 'Updated notes'

def test_unauthorized_contact_edit(test_client, session, test_family):
    # Create another family
    other_family = Family(name='Other Family')
    session.add(other_family)
    session.commit()
    
    # Create a contact in the other family
    other_contact = Contact(
        first_name='Other',
        last_name='Contact',
        email='other@example.com',
        role='babysitter',
        family_id=other_family.id
    )
    session.add(other_contact)
    session.commit()
    
    # Try to edit contact from other family
    response = test_client.get(f'/family/contacts/{other_contact.id}/edit', follow_redirects=True)
    assert b'Unauthorized access' in response.data

def test_access_without_family(app, session):
    # Create a user without a family
    user = User(
        first_name='No',
        last_name='Family',
        email='nofamily@example.com',
        password_hash='dummy-hash'
    )
    session.add(user)
    session.commit()
    
    # Create a test client for this user
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_csrf_token'] = 'test-csrf-token'
        sess['user_id'] = user.id
    
    # Try to access family management
    response = client.get('/family/members', follow_redirects=True)
    assert b'You need to create or join a family first' in response.data
    
    # Try to access contacts
    response = client.get('/family/contacts', follow_redirects=True)
    assert b'You need to create or join a family first' in response.data
