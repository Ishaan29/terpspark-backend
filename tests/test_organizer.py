"""
Phase 4: Organizer Management Unit Tests
Comprehensive tests for all organizer endpoints.
"""
import pytest
from fastapi import status
from datetime import date, time, datetime, timedelta
from app.models.event import Event, EventStatus
from app.models.user import User, UserRole
from app.models.registration import Registration, RegistrationStatus, CheckInStatus
from app.models.waitlist import WaitlistEntry, NotificationPreference
from app.core.security import get_password_hash, create_access_token
import uuid


# =============================================================================
# TEST: Health Check
# =============================================================================
class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test that health endpoint returns healthy status."""
        response = client.get("/api/organizer/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "TerpSpark Organizer API"
        assert data["version"] == "1.0.0"
        assert data["phase"] == "Phase 4: Organizer Management"


# =============================================================================
# TEST: Create Event (POST /api/organizer/events)
# =============================================================================
class TestCreateEvent:
    """Test event creation endpoint."""
    
    def test_create_event_success(self, client, sample_organizer, sample_category):
        """Test successful event creation."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Create event
        event_data = {
            "title": "New Test Event",
            "description": "This is a comprehensive test event description that meets the minimum length requirement of 50 characters.",
            "categoryId": sample_category.id,
            "date": (date.today() + timedelta(days=14)).isoformat(),
            "startTime": "10:00",
            "endTime": "12:00",
            "venue": "Test Venue",
            "location": "Test Location, Room 101",
            "capacity": 50,
            "tags": ["test", "workshop"]
        }
        
        response = client.post(
            "/api/organizer/events",
            json=event_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert "Event created successfully" in data["message"]
        assert data["event"]["title"] == "New Test Event"
        assert data["event"]["status"] == "pending"  # Events start as pending
    
    def test_create_event_unauthorized(self, client, sample_category):
        """Test event creation without authentication."""
        event_data = {
            "title": "New Test Event",
            "description": "This is a comprehensive test event description that meets the minimum length requirement of 50 characters.",
            "categoryId": sample_category.id,
            "date": (date.today() + timedelta(days=14)).isoformat(),
            "startTime": "10:00",
            "endTime": "12:00",
            "venue": "Test Venue",
            "location": "Test Location, Room 101",
            "capacity": 50
        }
        
        response = client.post("/api/organizer/events", json=event_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_event_not_approved_organizer(self, client, sample_pending_organizer, sample_category):
        """Test event creation by non-approved organizer."""
        # Create token manually for pending organizer to test endpoint rejection
        token_data = {
            "sub": sample_pending_organizer.id,
            "email": sample_pending_organizer.email,
            "role": sample_pending_organizer.role.value,
            "is_approved": sample_pending_organizer.is_approved
        }
        token = create_access_token(token_data)
        
        event_data = {
            "title": "New Test Event",
            "description": "This is a comprehensive test event description that meets the minimum length requirement of 50 characters.",
            "categoryId": sample_category.id,
            "date": (date.today() + timedelta(days=14)).isoformat(),
            "startTime": "10:00",
            "endTime": "12:00",
            "venue": "Test Venue",
            "location": "Test Location, Room 101",
            "capacity": 50
        }
        
        response = client.post(
            "/api/organizer/events",
            json=event_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "pending approval" in response.json()["detail"].lower()
    
    def test_create_event_student_forbidden(self, client, sample_student, sample_category):
        """Test event creation by student (should fail)."""
        # Login as student
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        event_data = {
            "title": "New Test Event",
            "description": "This is a comprehensive test event description that meets the minimum length requirement of 50 characters.",
            "categoryId": sample_category.id,
            "date": (date.today() + timedelta(days=14)).isoformat(),
            "startTime": "10:00",
            "endTime": "12:00",
            "venue": "Test Venue",
            "location": "Test Location, Room 101",
            "capacity": 50
        }
        
        response = client.post(
            "/api/organizer/events",
            json=event_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_create_event_invalid_category(self, client, sample_organizer):
        """Test event creation with invalid category."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        event_data = {
            "title": "New Test Event",
            "description": "This is a comprehensive test event description that meets the minimum length requirement of 50 characters.",
            "categoryId": str(uuid.uuid4()),  # Non-existent category
            "date": (date.today() + timedelta(days=14)).isoformat(),
            "startTime": "10:00",
            "endTime": "12:00",
            "venue": "Test Venue",
            "location": "Test Location, Room 101",
            "capacity": 50
        }
        
        response = client.post(
            "/api/organizer/events",
            json=event_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_create_event_past_date(self, client, sample_organizer, sample_category):
        """Test event creation with past date."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        event_data = {
            "title": "New Test Event",
            "description": "This is a comprehensive test event description that meets the minimum length requirement of 50 characters.",
            "categoryId": sample_category.id,
            "date": (date.today() - timedelta(days=1)).isoformat(),  # Past date
            "startTime": "10:00",
            "endTime": "12:00",
            "venue": "Test Venue",
            "location": "Test Location, Room 101",
            "capacity": 50
        }
        
        response = client.post(
            "/api/organizer/events",
            json=event_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_event_invalid_time(self, client, sample_organizer, sample_category):
        """Test event creation with end time before start time."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        event_data = {
            "title": "New Test Event",
            "description": "This is a comprehensive test event description that meets the minimum length requirement of 50 characters.",
            "categoryId": sample_category.id,
            "date": (date.today() + timedelta(days=14)).isoformat(),
            "startTime": "12:00",
            "endTime": "10:00",  # End before start
            "venue": "Test Venue",
            "location": "Test Location, Room 101",
            "capacity": 50
        }
        
        response = client.post(
            "/api/organizer/events",
            json=event_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# TEST: Get Organizer Events (GET /api/organizer/events)
# =============================================================================
class TestGetOrganizerEvents:
    """Test get organizer events endpoint."""
    
    def test_get_organizer_events_success(self, client, sample_organizer, sample_published_event):
        """Test successful retrieval of organizer events."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/organizer/events",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["events"]) >= 1
        assert data["statistics"]["total"] >= 1
        assert data["statistics"]["published"] >= 1
    
    def test_get_organizer_events_filter_by_status(self, client, sample_organizer, sample_published_event, sample_draft_event):
        """Test filtering events by status."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Filter by published
        response = client.get(
            "/api/organizer/events?status=published",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(event["status"] == "published" for event in data["events"])
        
        # Filter by draft
        response = client.get(
            "/api/organizer/events?status=draft",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(event["status"] == "draft" for event in data["events"])
    
    def test_get_organizer_events_invalid_status(self, client, sample_organizer):
        """Test filtering with invalid status."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/organizer/events?status=invalid",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_organizer_events_unauthorized(self, client):
        """Test getting events without authentication."""
        response = client.get("/api/organizer/events")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_organizer_events_empty(self, client, sample_other_organizer):
        """Test getting events for organizer with no events."""
        # Login as other organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "otherorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/organizer/events",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["events"]) == 0
        assert data["statistics"]["total"] == 0


# =============================================================================
# TEST: Update Event (PUT /api/organizer/events/{event_id})
# =============================================================================
class TestUpdateEvent:
    """Test update event endpoint."""
    
    def test_update_event_success(self, client, sample_organizer, sample_published_event):
        """Test successful event update."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        update_data = {
            "title": "Updated Event Title",
            "description": "This is an updated comprehensive test event description that meets the minimum length requirement of 50 characters."
        }
        
        response = client.put(
            f"/api/organizer/events/{sample_published_event.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["event"]["title"] == "Updated Event Title"
    
    def test_update_event_partial(self, client, sample_organizer, sample_published_event):
        """Test partial event update (only title)."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        update_data = {"title": "Partially Updated Title"}
        
        response = client.put(
            f"/api/organizer/events/{sample_published_event.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["event"]["title"] == "Partially Updated Title"
    
    def test_update_event_not_owner(self, client, sample_other_organizer, sample_published_event):
        """Test updating event owned by another organizer."""
        # Login as other organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "otherorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        update_data = {"title": "Unauthorized Update"}
        
        response = client.put(
            f"/api/organizer/events/{sample_published_event.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_update_event_not_found(self, client, sample_organizer):
        """Test updating non-existent event."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        update_data = {"title": "Updated Title"}
        
        response = client.put(
            f"/api/organizer/events/{str(uuid.uuid4())}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_event_cancelled(self, client, sample_organizer, sample_cancelled_event):
        """Test updating cancelled event (should fail)."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        update_data = {"title": "Updated Title"}
        
        response = client.put(
            f"/api/organizer/events/{sample_cancelled_event.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cancelled" in response.json()["detail"].lower()
    
    def test_update_event_capacity_below_registered(self, client, db, sample_organizer, sample_published_event, sample_registration):
        """Test reducing capacity below registered count."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Update event registered_count to 5
        sample_published_event.registered_count = 5
        db.add(sample_published_event)
        db.commit()
        
        update_data = {"capacity": 3}  # Less than registered count
        
        response = client.put(
            f"/api/organizer/events/{sample_published_event.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "capacity" in response.json()["detail"].lower()
    
    def test_update_event_admin_can_update(self, client, sample_admin, sample_published_event):
        """Test that admin can update any event."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        update_data = {"title": "Admin Updated Title"}
        
        response = client.put(
            f"/api/organizer/events/{sample_published_event.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# TEST: Cancel Event (POST /api/organizer/events/{event_id}/cancel)
# =============================================================================
class TestCancelEvent:
    """Test cancel event endpoint."""
    
    def test_cancel_event_success(self, client, sample_organizer, sample_published_event):
        """Test successful event cancellation."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            f"/api/organizer/events/{sample_published_event.id}/cancel",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "cancelled successfully" in data["message"].lower()
    
    def test_cancel_event_already_cancelled(self, client, sample_organizer, sample_cancelled_event):
        """Test cancelling already cancelled event."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            f"/api/organizer/events/{sample_cancelled_event.id}/cancel",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already cancelled" in response.json()["detail"].lower()
    
    def test_cancel_event_not_owner(self, client, sample_other_organizer, sample_published_event):
        """Test cancelling event owned by another organizer."""
        # Login as other organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "otherorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            f"/api/organizer/events/{sample_published_event.id}/cancel",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_cancel_event_not_found(self, client, sample_organizer):
        """Test cancelling non-existent event."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            f"/api/organizer/events/{str(uuid.uuid4())}/cancel",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TEST: Duplicate Event (POST /api/organizer/events/{event_id}/duplicate)
# =============================================================================
class TestDuplicateEvent:
    """Test duplicate event endpoint."""
    
    def test_duplicate_event_success(self, client, sample_organizer, sample_published_event):
        """Test successful event duplication."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            f"/api/organizer/events/{sample_published_event.id}/duplicate",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert " (Copy)" in data["event"]["title"]
        assert data["event"]["status"] == "draft"  # Duplicated events start as draft
        assert data["event"]["registeredCount"] == 0  # Registrations not copied
        assert data["event"]["waitlistCount"] == 0  # Waitlist not copied
    
    def test_duplicate_event_not_owner(self, client, sample_other_organizer, sample_published_event):
        """Test duplicating event owned by another organizer."""
        # Login as other organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "otherorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            f"/api/organizer/events/{sample_published_event.id}/duplicate",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_duplicate_event_not_found(self, client, sample_organizer):
        """Test duplicating non-existent event."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            f"/api/organizer/events/{str(uuid.uuid4())}/duplicate",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TEST: Get Organizer Statistics (GET /api/organizer/statistics)
# =============================================================================
class TestGetOrganizerStatistics:
    """Test get organizer statistics endpoint."""
    
    def test_get_statistics_success(self, client, sample_organizer, sample_published_event, sample_draft_event):
        """Test successful retrieval of organizer statistics."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/organizer/statistics",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "totalEvents" in data["statistics"]
        assert "upcomingEvents" in data["statistics"]
        assert "totalRegistrations" in data["statistics"]
        assert "eventsByStatus" in data["statistics"]
        assert data["statistics"]["totalEvents"] >= 2
    
    def test_get_statistics_unauthorized(self, client):
        """Test getting statistics without authentication."""
        response = client.get("/api/organizer/statistics")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# TEST: Get Event Attendees (GET /api/organizer/events/{event_id}/attendees)
# =============================================================================
class TestGetEventAttendees:
    """Test get event attendees endpoint."""
    
    def test_get_attendees_success(self, client, sample_organizer, sample_published_event, sample_registration):
        """Test successful retrieval of event attendees."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            f"/api/organizer/events/{sample_published_event.id}/attendees",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["attendees"]) >= 1
        assert data["statistics"]["totalRegistrations"] >= 1
        assert data["statistics"]["totalAttendees"] >= 1
    
    def test_get_attendees_filter_checked_in(self, client, sample_organizer, sample_published_event, sample_registration, sample_checked_in_registration):
        """Test filtering attendees by check-in status."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Filter by checked-in
        response = client.get(
            f"/api/organizer/events/{sample_published_event.id}/attendees?checkInStatus=checked_in",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(attendee["checkInStatus"] == "checked_in" for attendee in data["attendees"])
        
        # Filter by not checked-in
        response = client.get(
            f"/api/organizer/events/{sample_published_event.id}/attendees?checkInStatus=not_checked_in",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(attendee["checkInStatus"] == "not_checked_in" for attendee in data["attendees"])
    
    def test_get_attendees_not_owner(self, client, sample_other_organizer, sample_published_event):
        """Test getting attendees for event owned by another organizer."""
        # Login as other organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "otherorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            f"/api/organizer/events/{sample_published_event.id}/attendees",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_attendees_not_found(self, client, sample_organizer):
        """Test getting attendees for non-existent event."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            f"/api/organizer/events/{str(uuid.uuid4())}/attendees",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_attendees_empty(self, client, db, sample_organizer, sample_published_event):
        """Test getting attendees for event with no registrations."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Create event with no registrations
        empty_event = Event(
            id=str(uuid.uuid4()),
            title="Empty Event",
            description="This is an event with no registrations for testing purposes.",
            category_id=sample_published_event.category_id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=50,
            registered_count=0,
            status=EventStatus.PUBLISHED
        )
        db.add(empty_event)
        db.commit()
        db.refresh(empty_event)
        
        response = client.get(
            f"/api/organizer/events/{empty_event.id}/attendees",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["attendees"]) == 0
        assert data["statistics"]["totalRegistrations"] == 0


# =============================================================================
# TEST: Export Attendees CSV (GET /api/organizer/events/{event_id}/attendees/export)
# =============================================================================
class TestExportAttendeesCSV:
    """Test export attendees CSV endpoint."""
    
    def test_export_attendees_csv_success(self, client, sample_organizer, sample_published_event, sample_registration):
        """Test successful CSV export."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            f"/api/organizer/events/{sample_published_event.id}/attendees/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "attendees_" in response.headers["content-disposition"]
        
        # Check CSV content
        csv_content = response.text
        assert "Name" in csv_content
        assert "Email" in csv_content
        assert "Registration Date" in csv_content
    
    def test_export_attendees_csv_not_owner(self, client, sample_other_organizer, sample_published_event):
        """Test exporting CSV for event owned by another organizer."""
        # Login as other organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "otherorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            f"/api/organizer/events/{sample_published_event.id}/attendees/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_export_attendees_csv_not_found(self, client, sample_organizer):
        """Test exporting CSV for non-existent event."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            f"/api/organizer/events/{str(uuid.uuid4())}/attendees/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TEST: Check-in Attendee (POST /api/organizer/events/{event_id}/check-in/{registration_id})
# =============================================================================
class TestCheckInAttendee:
    """Test check-in attendee endpoint."""
    
    def test_check_in_attendee_success(self, client, sample_organizer, sample_published_event, sample_registration):
        """Test successful attendee check-in."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            f"/api/organizer/events/{sample_published_event.id}/check-in/{sample_registration.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["registration"]["checkInStatus"] == "checked_in"
        assert data["registration"]["checkedInAt"] is not None
    
    def test_check_in_attendee_already_checked_in(self, client, sample_organizer, sample_published_event, sample_checked_in_registration):
        """Test checking in already checked-in attendee."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            f"/api/organizer/events/{sample_published_event.id}/check-in/{sample_checked_in_registration.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already checked in" in response.json()["detail"].lower()
    
    def test_check_in_attendee_wrong_event(self, client, db, sample_organizer, sample_published_event, sample_registration):
        """Test checking in registration for different event."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Create another event
        other_event = Event(
            id=str(uuid.uuid4()),
            title="Other Event",
            description="This is another event for testing check-in validation.",
            category_id=sample_published_event.category_id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=50,
            status=EventStatus.PUBLISHED
        )
        db.add(other_event)
        db.commit()
        db.refresh(other_event)
        
        # Try to check in registration from different event
        response = client.post(
            f"/api/organizer/events/{other_event.id}/check-in/{sample_registration.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_check_in_attendee_not_owner(self, client, sample_other_organizer, sample_published_event, sample_registration):
        """Test checking in attendee for event owned by another organizer."""
        # Login as other organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "otherorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            f"/api/organizer/events/{sample_published_event.id}/check-in/{sample_registration.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_check_in_attendee_not_found(self, client, sample_organizer, sample_published_event):
        """Test checking in non-existent registration."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.post(
            f"/api/organizer/events/{sample_published_event.id}/check-in/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TEST: Send Announcement (POST /api/organizer/events/{event_id}/announcements)
# =============================================================================
class TestSendAnnouncement:
    """Test send announcement endpoint."""
    
    def test_send_announcement_success(self, client, sample_organizer, sample_published_event, sample_registration):
        """Test successful announcement sending."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        announcement_data = {
            "subject": "Important Event Update",
            "message": "This is a test announcement message that meets the minimum length requirement of 10 characters."
        }
        
        response = client.post(
            f"/api/organizer/events/{sample_published_event.id}/announcements",
            json=announcement_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["recipientCount"] >= 1
    
    def test_send_announcement_validation_error(self, client, sample_organizer, sample_published_event):
        """Test announcement with invalid data."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Subject too short
        announcement_data = {
            "subject": "Hi",
            "message": "This is a test announcement message."
        }
        
        response = client.post(
            f"/api/organizer/events/{sample_published_event.id}/announcements",
            json=announcement_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Message too short
        announcement_data = {
            "subject": "Important Update",
            "message": "Short"
        }
        
        response = client.post(
            f"/api/organizer/events/{sample_published_event.id}/announcements",
            json=announcement_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_send_announcement_not_owner(self, client, sample_other_organizer, sample_published_event):
        """Test sending announcement for event owned by another organizer."""
        # Login as other organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "otherorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        announcement_data = {
            "subject": "Important Update",
            "message": "This is a test announcement message that meets the minimum length requirement."
        }
        
        response = client.post(
            f"/api/organizer/events/{sample_published_event.id}/announcements",
            json=announcement_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_send_announcement_not_found(self, client, sample_organizer):
        """Test sending announcement for non-existent event."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        announcement_data = {
            "subject": "Important Update",
            "message": "This is a test announcement message that meets the minimum length requirement."
        }
        
        response = client.post(
            f"/api/organizer/events/{str(uuid.uuid4())}/announcements",
            json=announcement_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_send_announcement_no_registrations(self, client, db, sample_organizer, sample_published_event):
        """Test sending announcement to event with no registrations."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Create event with no registrations
        empty_event = Event(
            id=str(uuid.uuid4()),
            title="Empty Event",
            description="This is an event with no registrations for testing purposes.",
            category_id=sample_published_event.category_id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=50,
            registered_count=0,
            status=EventStatus.PUBLISHED
        )
        db.add(empty_event)
        db.commit()
        db.refresh(empty_event)
        
        announcement_data = {
            "subject": "Important Update",
            "message": "This is a test announcement message that meets the minimum length requirement."
        }
        
        response = client.post(
            f"/api/organizer/events/{empty_event.id}/announcements",
            json=announcement_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["recipientCount"] == 0


# =============================================================================
# TEST: Get Event Waitlist (GET /api/organizer/events/{event_id}/waitlist)
# =============================================================================
class TestGetEventWaitlist:
    """Test get event waitlist endpoint."""
    
    def test_get_waitlist_success(self, client, sample_organizer, sample_full_event, sample_waitlist_entry):
        """Test successful retrieval of event waitlist."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            f"/api/organizer/events/{sample_full_event.id}/waitlist",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["waitlist"]) >= 1
        assert data["totalCount"] >= 1
        assert data["waitlist"][0]["position"] == 1
    
    def test_get_waitlist_not_owner(self, client, sample_other_organizer, sample_full_event):
        """Test getting waitlist for event owned by another organizer."""
        # Login as other organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "otherorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            f"/api/organizer/events/{sample_full_event.id}/waitlist",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_waitlist_not_found(self, client, sample_organizer):
        """Test getting waitlist for non-existent event."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            f"/api/organizer/events/{str(uuid.uuid4())}/waitlist",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_waitlist_empty(self, client, sample_organizer, sample_published_event):
        """Test getting waitlist for event with no waitlist entries."""
        # Login as organizer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testorganizer@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            f"/api/organizer/events/{sample_published_event.id}/waitlist",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["waitlist"]) == 0
        assert data["totalCount"] == 0

