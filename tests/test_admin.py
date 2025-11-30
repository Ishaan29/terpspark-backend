"""
Phase 5: Admin Console Unit Tests
Comprehensive tests for all admin endpoints.
"""
import pytest
from fastapi import status
from datetime import date, time, datetime, timedelta
from app.models.event import Event, EventStatus
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.venue import Venue
from app.models.organizer_approval import OrganizerApprovalRequest, ApprovalStatus
from app.models.audit_log import AuditLog, AuditAction, TargetType
from app.models.registration import Registration, RegistrationStatus, CheckInStatus
from app.core.security import create_access_token
import uuid


# =============================================================================
# TEST: Organizer Approvals
# =============================================================================
class TestGetOrganizerApprovals:
    """Test get organizer approvals endpoint."""
    
    def test_get_organizer_approvals_success(self, client, sample_admin, sample_organizer_approval_request):
        """Test successful retrieval of organizer approval requests."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/approvals/organizers",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "requests" in data
        assert len(data["requests"]) >= 1
    
    def test_get_organizer_approvals_filter_pending(self, client, sample_admin, sample_organizer_approval_request):
        """Test filtering by pending status."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/approvals/organizers?status=pending",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(req["status"] == "pending" for req in data["requests"])
    
    def test_get_organizer_approvals_filter_all(self, client, db, sample_admin, sample_organizer_approval_request):
        """Test filtering by all statuses."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Create an approved request
        approved_request = OrganizerApprovalRequest(
            id=str(uuid.uuid4()),
            user_id=sample_organizer_approval_request.user_id,
            reason="Another reason",
            status=ApprovalStatus.APPROVED,
            reviewed_by=sample_admin.id,
            reviewed_at=datetime.now()
        )
        db.add(approved_request)
        db.commit()
        
        response = client.get(
            "/api/admin/approvals/organizers?status=all",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["requests"]) >= 2
    
    def test_get_organizer_approvals_unauthorized(self, client):
        """Test getting approvals without authentication."""
        response = client.get("/api/admin/approvals/organizers")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_organizer_approvals_not_admin(self, client, sample_student):
        """Test getting approvals as non-admin."""
        # Login as student
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/approvals/organizers",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestApproveOrganizer:
    """Test approve organizer endpoint."""
    
    def test_approve_organizer_success(self, client, sample_admin, sample_organizer_approval_request):
        """Test successful organizer approval."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        approval_data = {
            "notes": "Approved for organizing events"
        }
        
        response = client.post(
            f"/api/admin/approvals/organizers/{sample_organizer_approval_request.id}/approve",
            json=approval_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "approved successfully" in data["message"].lower()
    
    def test_approve_organizer_not_found(self, client, sample_admin):
        """Test approving non-existent request."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        approval_data = {"notes": "Test notes"}
        
        response = client.post(
            f"/api/admin/approvals/organizers/{str(uuid.uuid4())}/approve",
            json=approval_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_approve_organizer_already_approved(self, client, db, sample_admin, sample_organizer_approval_request):
        """Test approving already approved request."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Approve the request first
        sample_organizer_approval_request.status = ApprovalStatus.APPROVED
        sample_organizer_approval_request.reviewed_by = sample_admin.id
        sample_organizer_approval_request.reviewed_at = datetime.now()
        db.commit()
        
        approval_data = {"notes": "Test notes"}
        
        response = client.post(
            f"/api/admin/approvals/organizers/{sample_organizer_approval_request.id}/approve",
            json=approval_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestRejectOrganizer:
    """Test reject organizer endpoint."""
    
    def test_reject_organizer_success(self, client, sample_admin, sample_organizer_approval_request):
        """Test successful organizer rejection."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        rejection_data = {
            "notes": "Insufficient experience or qualifications"
        }
        
        response = client.post(
            f"/api/admin/approvals/organizers/{sample_organizer_approval_request.id}/reject",
            json=rejection_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "rejected" in data["message"].lower()
    
    def test_reject_organizer_not_found(self, client, sample_admin):
        """Test rejecting non-existent request."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        rejection_data = {"notes": "Test rejection reason"}
        
        response = client.post(
            f"/api/admin/approvals/organizers/{str(uuid.uuid4())}/reject",
            json=rejection_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TEST: Event Approvals
# =============================================================================
class TestGetPendingEvents:
    """Test get pending events endpoint."""
    
    def test_get_pending_events_success(self, client, sample_admin, sample_pending_event):
        """Test successful retrieval of pending events."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/approvals/events",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "events" in data
        assert len(data["events"]) >= 1
        assert data["events"][0]["status"] == "pending"
    
    def test_get_pending_events_unauthorized(self, client):
        """Test getting pending events without authentication."""
        response = client.get("/api/admin/approvals/events")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestApproveEvent:
    """Test approve event endpoint."""
    
    def test_approve_event_success(self, client, sample_admin, sample_pending_event):
        """Test successful event approval."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        approval_data = {
            "notes": "Event approved and ready for publication"
        }
        
        response = client.post(
            f"/api/admin/approvals/events/{sample_pending_event.id}/approve",
            json=approval_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "approved and published" in data["message"].lower()
    
    def test_approve_event_not_found(self, client, sample_admin):
        """Test approving non-existent event."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        approval_data = {"notes": "Test notes"}
        
        response = client.post(
            f"/api/admin/approvals/events/{str(uuid.uuid4())}/approve",
            json=approval_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_approve_event_not_pending(self, client, sample_admin, sample_published_event):
        """Test approving non-pending event."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        approval_data = {"notes": "Test notes"}
        
        response = client.post(
            f"/api/admin/approvals/events/{sample_published_event.id}/approve",
            json=approval_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestRejectEvent:
    """Test reject event endpoint."""
    
    def test_reject_event_success(self, client, sample_admin, sample_pending_event):
        """Test successful event rejection."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        rejection_data = {
            "notes": "Event does not meet quality standards"
        }
        
        response = client.post(
            f"/api/admin/approvals/events/{sample_pending_event.id}/reject",
            json=rejection_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "rejected" in data["message"].lower()
    
    def test_reject_event_not_found(self, client, sample_admin):
        """Test rejecting non-existent event."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        rejection_data = {"notes": "Test rejection reason"}
        
        response = client.post(
            f"/api/admin/approvals/events/{str(uuid.uuid4())}/reject",
            json=rejection_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TEST: Category Management
# =============================================================================
class TestGetAllCategories:
    """Test get all categories endpoint."""
    
    def test_get_all_categories_success(self, client, sample_admin, sample_category):
        """Test successful retrieval of all categories."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/categories",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) >= 1
    
    def test_get_all_categories_include_inactive(self, client, sample_admin, sample_category, sample_inactive_category):
        """Test including inactive categories."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/categories?includeInactive=true",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["categories"]) >= 2
        assert any(cat["isActive"] is False for cat in data["categories"])


class TestCreateCategory:
    """Test create category endpoint."""
    
    def test_create_category_success(self, client, sample_admin):
        """Test successful category creation."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        category_data = {
            "name": "New Test Category",
            "slug": "new-test-category",
            "description": "A new test category",
            "color": "#FF5733",
            "icon": "new-icon"
        }
        
        response = client.post(
            "/api/admin/categories",
            json=category_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["message"] == "Category created successfully"
        assert data["category"]["name"] == "New Test Category"
    
    def test_create_category_auto_slug(self, client, sample_admin):
        """Test category creation with auto-generated slug."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        category_data = {
            "name": "Auto Slug Category",
            "color": "#FF5733"
        }
        
        response = client.post(
            "/api/admin/categories",
            json=category_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "auto-slug-category" in data["category"]["slug"]
    
    def test_create_category_duplicate_slug(self, client, sample_admin, sample_category):
        """Test creating category with duplicate slug."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        category_data = {
            "name": "Different Name",
            "slug": sample_category.slug,  # Duplicate slug
            "color": "#FF5733"
        }
        
        response = client.post(
            "/api/admin/categories",
            json=category_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT


class TestUpdateCategory:
    """Test update category endpoint."""
    
    def test_update_category_success(self, client, sample_admin, sample_category):
        """Test successful category update."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        update_data = {
            "name": "Updated Category Name",
            "description": "Updated description"
        }
        
        response = client.put(
            f"/api/admin/categories/{sample_category.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["category"]["name"] == "Updated Category Name"
    
    def test_update_category_not_found(self, client, sample_admin):
        """Test updating non-existent category."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        update_data = {"name": "Updated Name"}
        
        response = client.put(
            f"/api/admin/categories/{str(uuid.uuid4())}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestToggleCategory:
    """Test toggle category (retire/reactivate) endpoint."""
    
    def test_toggle_category_retire_success(self, client, sample_admin, sample_category):
        """Test successful category retirement."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.delete(
            f"/api/admin/categories/{sample_category.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "retired" in data["message"].lower()
    
    def test_toggle_category_reactivate_success(self, client, sample_admin, sample_inactive_category):
        """Test successful category reactivation."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.delete(
            f"/api/admin/categories/{sample_inactive_category.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "reactivated" in data["message"].lower()
    
    def test_toggle_category_with_events(self, client, db, sample_admin, sample_category, sample_published_event):
        """Test retiring category with active events."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Ensure event uses this category
        sample_published_event.category_id = sample_category.id
        db.commit()
        
        response = client.delete(
            f"/api/admin/categories/{sample_category.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "active event" in response.json()["detail"].lower()


# =============================================================================
# TEST: Venue Management
# =============================================================================
class TestGetAllVenues:
    """Test get all venues endpoint."""
    
    def test_get_all_venues_success(self, client, sample_admin, sample_venue):
        """Test successful retrieval of all venues."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/venues",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "venues" in data
        assert len(data["venues"]) >= 1
    
    def test_get_all_venues_include_inactive(self, client, sample_admin, sample_venue, sample_inactive_venue):
        """Test including inactive venues."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/venues?includeInactive=true",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["venues"]) >= 2
        assert any(venue["isActive"] is False for venue in data["venues"])


class TestCreateVenue:
    """Test create venue endpoint."""
    
    def test_create_venue_success(self, client, sample_admin):
        """Test successful venue creation."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        venue_data = {
            "name": "New Test Venue",
            "building": "New Test Building",
            "capacity": 200,
            "facilities": ["Projector", "WiFi", "Whiteboard"]
        }
        
        response = client.post(
            "/api/admin/venues",
            json=venue_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["message"] == "Venue created successfully"
        assert data["venue"]["name"] == "New Test Venue"
        assert data["venue"]["capacity"] == 200


class TestUpdateVenue:
    """Test update venue endpoint."""
    
    def test_update_venue_success(self, client, sample_admin, sample_venue):
        """Test successful venue update."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        update_data = {
            "name": "Updated Venue Name",
            "capacity": 150
        }
        
        response = client.put(
            f"/api/admin/venues/{sample_venue.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["venue"]["name"] == "Updated Venue Name"
        assert data["venue"]["capacity"] == 150
    
    def test_update_venue_not_found(self, client, sample_admin):
        """Test updating non-existent venue."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        update_data = {"name": "Updated Name"}
        
        response = client.put(
            f"/api/admin/venues/{str(uuid.uuid4())}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestToggleVenue:
    """Test toggle venue (retire/reactivate) endpoint."""
    
    def test_toggle_venue_retire_success(self, client, sample_admin, sample_venue):
        """Test successful venue retirement."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.delete(
            f"/api/admin/venues/{sample_venue.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "retired" in data["message"].lower()
    
    def test_toggle_venue_reactivate_success(self, client, sample_admin, sample_inactive_venue):
        """Test successful venue reactivation."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.delete(
            f"/api/admin/venues/{sample_inactive_venue.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "reactivated" in data["message"].lower()


# =============================================================================
# TEST: Audit Logs
# =============================================================================
class TestGetAuditLogs:
    """Test get audit logs endpoint."""
    
    def test_get_audit_logs_success(self, client, db, sample_admin):
        """Test successful retrieval of audit logs."""
        # Create an audit log entry
        audit_log = AuditLog(
            id=str(uuid.uuid4()),
            action=AuditAction.ORGANIZER_APPROVED,
            actor_id=sample_admin.id,
            actor_name=sample_admin.name,
            actor_role=sample_admin.role.value,
            target_type=TargetType.USER,
            target_id=str(uuid.uuid4()),
            target_name="Test User",
            details="Test audit log entry",
            timestamp=datetime.now()
        )
        db.add(audit_log)
        db.commit()
        
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/audit-logs",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "logs" in data
        assert "pagination" in data
        assert len(data["logs"]) >= 1
    
    def test_get_audit_logs_filter_by_action(self, client, db, sample_admin):
        """Test filtering audit logs by action."""
        # Create audit logs with different actions
        log1 = AuditLog(
            id=str(uuid.uuid4()),
            action=AuditAction.ORGANIZER_APPROVED,
            actor_id=sample_admin.id,
            actor_name=sample_admin.name,
            actor_role=sample_admin.role.value,
            target_type=TargetType.USER,
            target_id=str(uuid.uuid4()),
            target_name="Test User",
            details="Test log 1",
            timestamp=datetime.now()
        )
        log2 = AuditLog(
            id=str(uuid.uuid4()),
            action=AuditAction.EVENT_APPROVED,
            actor_id=sample_admin.id,
            actor_name=sample_admin.name,
            actor_role=sample_admin.role.value,
            target_type=TargetType.EVENT,
            target_id=str(uuid.uuid4()),
            target_name="Test Event",
            details="Test log 2",
            timestamp=datetime.now()
        )
        db.add_all([log1, log2])
        db.commit()
        
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/audit-logs?action=ORGANIZER_APPROVED",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(log["action"] == "ORGANIZER_APPROVED" for log in data["logs"])
    
    def test_get_audit_logs_pagination(self, client, db, sample_admin):
        """Test audit logs pagination."""
        # Create multiple audit logs
        logs = []
        for i in range(5):
            log = AuditLog(
                id=str(uuid.uuid4()),
                action=AuditAction.ORGANIZER_APPROVED,
                actor_id=sample_admin.id,
                actor_name=sample_admin.name,
                actor_role=sample_admin.role.value,
                target_type=TargetType.USER,
                target_id=str(uuid.uuid4()),
                target_name=f"Test User {i}",
                details=f"Test log {i}",
                timestamp=datetime.now()
            )
            logs.append(log)
        db.add_all(logs)
        db.commit()
        
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/audit-logs?page=1&limit=2",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["logs"]) <= 2
        assert data["pagination"]["currentPage"] == 1
        assert data["pagination"]["itemsPerPage"] == 2


# =============================================================================
# TEST: Analytics & Dashboard
# =============================================================================
class TestGetAnalytics:
    """Test get analytics endpoint."""
    
    def test_get_analytics_success(self, client, db, sample_admin, sample_category, sample_published_event, sample_registration):
        """Test successful retrieval of analytics."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/analytics",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "analytics" in data
        analytics = data["analytics"]
        assert "summary" in analytics
        assert "byCategory" in analytics
        assert "byDate" in analytics
        assert "topEvents" in analytics
        assert "organizerStats" in analytics
    
    def test_get_analytics_with_filters(self, client, db, sample_admin, sample_category, sample_published_event):
        """Test analytics with date filters."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        start_date = (date.today() - timedelta(days=30)).isoformat()
        end_date = date.today().isoformat()
        
        response = client.get(
            f"/api/admin/analytics?startDate={start_date}&endDate={end_date}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "analytics" in data


class TestGetDashboardStats:
    """Test get dashboard stats endpoint."""
    
    def test_get_dashboard_stats_success(self, client, db, sample_admin, sample_organizer_approval_request, sample_pending_event):
        """Test successful retrieval of dashboard stats."""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "testadmin@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "stats" in data
        stats = data["stats"]
        assert "pendingOrganizers" in stats
        assert "pendingEvents" in stats
        assert "totalPending" in stats
        assert "totalEvents" in stats
        assert "totalRegistrations" in stats
        assert "totalAttendance" in stats
        assert "activeOrganizers" in stats
        assert "activeStudents" in stats
        assert stats["pendingOrganizers"] >= 1
        assert stats["pendingEvents"] >= 1

