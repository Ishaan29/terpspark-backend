"""
Phase 3: Student Registration Flow Unit Tests
Comprehensive tests for all registration endpoints.
"""
import pytest
from fastapi import status
from datetime import date, time, datetime, timedelta
from app.models.registration import Registration, RegistrationStatus, CheckInStatus
from app.models.event import Event, EventStatus
from app.models.user import User, UserRole
from app.core.security import get_password_hash
import uuid


# =============================================================================
# TEST: Health Check
# =============================================================================
class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test that health endpoint returns healthy status."""
        response = client.get("/api/registrations/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "TerpSpark Registration API"
        assert data["version"] == "1.0.0"
        assert data["phase"] == "Phase 3: Student Registration Flow"


# =============================================================================
# TEST: Register for Event (POST /api/registrations)
# =============================================================================
class TestRegisterForEvent:
    """Test registration endpoint."""
    
    def test_register_success_no_guests(self, client, sample_student, sample_published_event):
        """Test successful registration without guests."""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Register for event
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": sample_published_event.id,
                "guests": [],
                "notificationPreference": "email"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "registration" in data
        assert data["registration"]["status"] == "confirmed"
        assert data["registration"]["ticketCode"] is not None
        assert data["registration"]["qrCode"] is not None
        assert data["registration"]["checkInStatus"] == "not_checked_in"
        assert len(data["registration"]["guests"]) == 0
    
    def test_register_success_with_one_guest(self, client, sample_student, sample_published_event):
        """Test successful registration with one guest."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": sample_published_event.id,
                "guests": [
                    {
                        "name": "Guest One",
                        "email": "guest1@umd.edu"
                    }
                ],
                "notificationPreference": "email"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["registration"]["guests"]) == 1
        assert data["registration"]["guests"][0]["name"] == "Guest One"
        assert data["registration"]["guests"][0]["email"] == "guest1@umd.edu"
    
    def test_register_success_with_two_guests(self, client, sample_student, sample_published_event):
        """Test successful registration with two guests (max allowed)."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": sample_published_event.id,
                "guests": [
                    {
                        "name": "Guest One",
                        "email": "guest1@umd.edu"
                    },
                    {
                        "name": "Guest Two",
                        "email": "guest2@umd.edu"
                    }
                ],
                "notificationPreference": "email"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["registration"]["guests"]) == 2
    
    def test_register_unauthorized(self, client, sample_published_event):
        """Test registration without authentication fails."""
        response = client.post(
            "/api/registrations",
            json={
                "eventId": sample_published_event.id,
                "guests": []
            }
        )
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_register_event_not_found(self, client, sample_student):
        """Test registration for non-existent event fails."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": str(uuid.uuid4()),
                "guests": []
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_register_event_not_published(self, client, db, sample_student, sample_category, sample_organizer):
        """Test registration for non-published event fails."""
        # Create draft event
        draft_event = Event(
            id=str(uuid.uuid4()),
            title="Draft Event",
            description="This is a draft event.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            registered_count=0,
            waitlist_count=0,
            status=EventStatus.DRAFT
        )
        db.add(draft_event)
        db.commit()
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": draft_event.id,
                "guests": []
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_past_event(self, client, db, sample_student, sample_category, sample_organizer):
        """Test registration for past event fails."""
        # Create past event
        past_event = Event(
            id=str(uuid.uuid4()),
            title="Past Event",
            description="This is a past event.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() - timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            registered_count=0,
            waitlist_count=0,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now() - timedelta(days=2)
        )
        db.add(past_event)
        db.commit()
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": past_event.id,
                "guests": []
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_duplicate(self, client, sample_student, sample_published_event, sample_registration):
        """Test duplicate registration fails."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": sample_published_event.id,
                "guests": []
            }
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT
    
    def test_register_too_many_guests(self, client, sample_student, sample_published_event):
        """Test registration with more than 2 guests fails."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": sample_published_event.id,
                "guests": [
                    {"name": "Guest 1", "email": "guest1@umd.edu"},
                    {"name": "Guest 2", "email": "guest2@umd.edu"},
                    {"name": "Guest 3", "email": "guest3@umd.edu"}
                ]
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_invalid_guest_email(self, client, sample_student, sample_published_event):
        """Test registration with non-UMD guest email fails."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": sample_published_event.id,
                "guests": [
                    {
                        "name": "Guest One",
                        "email": "guest@gmail.com"
                    }
                ]
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_duplicate_guest_emails(self, client, sample_student, sample_published_event):
        """Test registration with duplicate guest emails fails."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": sample_published_event.id,
                "guests": [
                    {
                        "name": "Guest One",
                        "email": "guest@umd.edu"
                    },
                    {
                        "name": "Guest Two",
                        "email": "guest@umd.edu"
                    }
                ]
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_event_full(self, client, db, sample_student, sample_category, sample_organizer):
        """Test registration for full event fails."""
        # Create full event
        full_event = Event(
            id=str(uuid.uuid4()),
            title="Full Event",
            description="This event is full.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=10,
            registered_count=10,  # Full
            waitlist_count=0,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(full_event)
        db.commit()
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": full_event.id,
                "guests": []
            }
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT
    
    def test_register_insufficient_capacity_with_guests(self, client, db, sample_student, sample_category, sample_organizer):
        """Test registration fails when capacity insufficient for user + guests."""
        # Create event with only 1 spot left
        event = Event(
            id=str(uuid.uuid4()),
            title="Almost Full Event",
            description="This event has only 1 spot left.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=10,
            registered_count=9,  # Only 1 spot left
            waitlist_count=0,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event)
        db.commit()
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Try to register with 1 guest (needs 2 spots)
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": event.id,
                "guests": [
                    {
                        "name": "Guest One",
                        "email": "guest1@umd.edu"
                    }
                ]
            }
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT
    
    def test_register_guest_already_registered(self, client, db, sample_student, sample_published_event):
        """Test registration fails when guest is already registered."""
        # Create another user who will be the guest
        guest_user = User(
            id=str(uuid.uuid4()),
            email="guestuser@umd.edu",
            password=get_password_hash("password123"),
            name="Guest User",
            role=UserRole.STUDENT,
            is_approved=True
        )
        db.add(guest_user)
        
        # Register guest user for the event
        guest_registration = Registration(
            id=str(uuid.uuid4()),
            user_id=guest_user.id,
            event_id=sample_published_event.id,
            status=RegistrationStatus.CONFIRMED,
            ticket_code="TKT-GUEST-123",
            qr_code="data:image/png;base64,test",
            check_in_status=CheckInStatus.NOT_CHECKED_IN
        )
        db.add(guest_registration)
        db.commit()
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Try to register with guest who is already registered
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": sample_published_event.id,
                "guests": [
                    {
                        "name": "Guest User",
                        "email": "guestuser@umd.edu"
                    }
                ]
            }
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT
    
    def test_register_terpmail_email(self, client, sample_student, sample_published_event):
        """Test registration with terpmail.umd.edu guest email succeeds."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "eventId": sample_published_event.id,
                "guests": [
                    {
                        "name": "Guest One",
                        "email": "guest@terpmail.umd.edu"
                    }
                ]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["registration"]["guests"]) == 1


# =============================================================================
# TEST: Get User Registrations (GET /api/registrations)
# =============================================================================
class TestGetUserRegistrations:
    """Test get user registrations endpoint."""
    
    def test_get_registrations_success(self, client, sample_student, sample_registration):
        """Test successful retrieval of user registrations."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "registrations" in data
        assert len(data["registrations"]) >= 1
        assert data["registrations"][0]["id"] == sample_registration.id
    
    def test_get_registrations_with_status_filter(self, client, sample_student, sample_registration):
        """Test get registrations with status filter."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Get confirmed registrations
        response = client.get(
            "/api/registrations?status=confirmed",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(reg["status"] == "confirmed" for reg in data["registrations"])
    
    def test_get_registrations_cancelled(self, client, db, sample_student, sample_published_event):
        """Test get cancelled registrations."""
        # Create cancelled registration
        cancelled_reg = Registration(
            id=str(uuid.uuid4()),
            user_id=sample_student.id,
            event_id=sample_published_event.id,
            status=RegistrationStatus.CANCELLED,
            ticket_code="TKT-CANCELLED-123",
            qr_code="data:image/png;base64,test",
            check_in_status=CheckInStatus.NOT_CHECKED_IN,
            cancelled_at=datetime.now()
        )
        db.add(cancelled_reg)
        db.commit()
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/registrations?status=cancelled",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(reg["status"] == "cancelled" for reg in data["registrations"])
    
    def test_get_registrations_all_status(self, client, sample_student, sample_registration):
        """Test get all registrations regardless of status."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/registrations?status=all",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "registrations" in data
    
    def test_get_registrations_invalid_status(self, client, sample_student):
        """Test get registrations with invalid status parameter."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/registrations?status=invalid",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_registrations_unauthorized(self, client):
        """Test get registrations without authentication fails."""
        response = client.get("/api/registrations")
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_get_registrations_empty(self, client, db):
        """Test get registrations for user with no registrations."""
        # Create new student with no registrations
        new_student = User(
            id=str(uuid.uuid4()),
            email="newstudent@umd.edu",
            password=get_password_hash("password123"),
            name="New Student",
            role=UserRole.STUDENT,
            is_approved=True
        )
        db.add(new_student)
        db.commit()
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "newstudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/registrations",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["registrations"]) == 0


# =============================================================================
# TEST: Cancel Registration (DELETE /api/registrations/{id})
# =============================================================================
class TestCancelRegistration:
    """Test cancel registration endpoint."""
    
    def test_cancel_registration_success(self, client, sample_student, sample_registration):
        """Test successful cancellation of registration."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.delete(
            f"/api/registrations/{sample_registration.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "message" in data
    
    def test_cancel_registration_not_found(self, client, sample_student):
        """Test cancellation of non-existent registration fails."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.delete(
            f"/api/registrations/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_cancel_registration_unauthorized(self, client, sample_registration):
        """Test cancellation without authentication fails."""
        response = client.delete(f"/api/registrations/{sample_registration.id}")
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_cancel_other_user_registration(self, client, db, sample_student, sample_published_event):
        """Test cancellation of another user's registration fails."""
        # Create another student
        other_student = User(
            id=str(uuid.uuid4()),
            email="otherstudent@umd.edu",
            password=get_password_hash("password123"),
            name="Other Student",
            role=UserRole.STUDENT,
            is_approved=True
        )
        db.add(other_student)
        
        # Create registration for other student
        other_registration = Registration(
            id=str(uuid.uuid4()),
            user_id=other_student.id,
            event_id=sample_published_event.id,
            status=RegistrationStatus.CONFIRMED,
            ticket_code="TKT-OTHER-123",
            qr_code="data:image/png;base64,test",
            check_in_status=CheckInStatus.NOT_CHECKED_IN
        )
        db.add(other_registration)
        db.commit()
        
        # Login as first student
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Try to cancel other student's registration
        response = client.delete(
            f"/api/registrations/{other_registration.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_cancel_already_cancelled(self, client, db, sample_student, sample_published_event):
        """Test cancellation of already cancelled registration fails."""
        # Create cancelled registration
        cancelled_reg = Registration(
            id=str(uuid.uuid4()),
            user_id=sample_student.id,
            event_id=sample_published_event.id,
            status=RegistrationStatus.CANCELLED,
            ticket_code="TKT-CANCELLED-123",
            qr_code="data:image/png;base64,test",
            check_in_status=CheckInStatus.NOT_CHECKED_IN,
            cancelled_at=datetime.now()
        )
        db.add(cancelled_reg)
        db.commit()
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.delete(
            f"/api/registrations/{cancelled_reg.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_cancel_registration_with_guests(self, client, db, sample_student, sample_published_event):
        """Test cancellation of registration with guests updates capacity correctly."""
        # Create registration with guests
        registration = Registration(
            id=str(uuid.uuid4()),
            user_id=sample_student.id,
            event_id=sample_published_event.id,
            status=RegistrationStatus.CONFIRMED,
            ticket_code="TKT-GUESTS-123",
            qr_code="data:image/png;base64,test",
            check_in_status=CheckInStatus.NOT_CHECKED_IN,
            guests=[
                {"name": "Guest One", "email": "guest1@umd.edu"},
                {"name": "Guest Two", "email": "guest2@umd.edu"}
            ]
        )
        db.add(registration)
        # Update event registered count
        sample_published_event.registered_count = 3  # User + 2 guests
        db.commit()
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.delete(
            f"/api/registrations/{registration.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify event capacity was updated
        db.refresh(sample_published_event)
        assert sample_published_event.registered_count == 0

