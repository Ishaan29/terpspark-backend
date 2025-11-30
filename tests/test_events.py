"""
Phase 2: Event Discovery & Browse Unit Tests
Comprehensive tests for all Phase 2 endpoints.
"""
import pytest
from fastapi import status
from datetime import date, time, datetime, timedelta
from app.models.event import Event, EventStatus
from app.models.category import Category
from app.models.venue import Venue
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
        response = client.get("/api/events/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "TerpSpark Events API"
        assert data["version"] == "1.0.0"
        assert data["phase"] == "Phase 2: Event Discovery & Browse"


# =============================================================================
# TEST: Get Categories (GET /api/categories)
# =============================================================================
class TestGetCategories:
    """Test categories endpoint."""
    
    def test_get_categories_success(self, client, sample_category):
        """Test successful retrieval of categories."""
        response = client.get("/api/categories")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "categories" in data
        assert isinstance(data["categories"], list)
        assert len(data["categories"]) >= 1
        
        # Check category structure
        category = data["categories"][0]
        assert "id" in category
        assert "name" in category
        assert "slug" in category
        assert "color" in category
        assert "isActive" in category
    
    def test_get_categories_only_active(self, client, db):
        """Test that only active categories are returned."""
        # Create active category
        active_cat = Category(
            id=str(uuid.uuid4()),
            name="Active Category",
            slug="active-category",
            color="blue",
            is_active=True
        )
        db.add(active_cat)
        
        # Create inactive category
        inactive_cat = Category(
            id=str(uuid.uuid4()),
            name="Inactive Category",
            slug="inactive-category",
            color="red",
            is_active=False
        )
        db.add(inactive_cat)
        db.commit()
        
        response = client.get("/api/categories")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        category_slugs = [cat["slug"] for cat in data["categories"]]
        assert "active-category" in category_slugs
        assert "inactive-category" not in category_slugs
    
    def test_get_categories_empty_list(self, client, db):
        """Test categories endpoint when no categories exist."""
        # Clear all categories
        db.query(Category).delete()
        db.commit()
        
        response = client.get("/api/categories")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["categories"] == []


# =============================================================================
# TEST: Get Venues (GET /api/venues)
# =============================================================================
class TestGetVenues:
    """Test venues endpoint."""
    
    def test_get_venues_success(self, client, sample_venue):
        """Test successful retrieval of venues."""
        response = client.get("/api/venues")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "venues" in data
        assert isinstance(data["venues"], list)
        assert len(data["venues"]) >= 1
        
        # Check venue structure
        venue = data["venues"][0]
        assert "id" in venue
        assert "name" in venue
        assert "building" in venue
        assert "capacity" in venue
        assert "facilities" in venue
        assert "isActive" in venue
    
    def test_get_venues_only_active(self, client, db):
        """Test that only active venues are returned."""
        # Create active venue
        active_venue = Venue(
            id=str(uuid.uuid4()),
            name="Active Venue",
            building="Test Building",
            is_active=True
        )
        db.add(active_venue)
        
        # Create inactive venue
        inactive_venue = Venue(
            id=str(uuid.uuid4()),
            name="Inactive Venue",
            building="Test Building 2",
            is_active=False
        )
        db.add(inactive_venue)
        db.commit()
        
        response = client.get("/api/venues")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        venue_names = [venue["name"] for venue in data["venues"]]
        assert "Active Venue" in venue_names
        assert "Inactive Venue" not in venue_names
    
    def test_get_venues_with_facilities(self, client, db):
        """Test venues with facilities array."""
        venue = Venue(
            id=str(uuid.uuid4()),
            name="Tech Venue",
            building="Tech Building",
            capacity=100,
            facilities=["Projector", "WiFi", "Microphone"],
            is_active=True
        )
        db.add(venue)
        db.commit()
        
        response = client.get("/api/venues")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        tech_venue = next((v for v in data["venues"] if v["name"] == "Tech Venue"), None)
        assert tech_venue is not None
        assert tech_venue["facilities"] == ["Projector", "WiFi", "Microphone"]
    
    def test_get_venues_empty_list(self, client, db):
        """Test venues endpoint when no venues exist."""
        # Clear all venues
        db.query(Venue).delete()
        db.commit()
        
        response = client.get("/api/venues")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["venues"] == []


# =============================================================================
# TEST: Get Events List (GET /api/events)
# =============================================================================
class TestGetEvents:
    """Test events list endpoint."""
    
    def test_get_events_success(self, client, sample_student, sample_published_event):
        """Test successful retrieval of events."""
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/events",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "events" in data
        assert "pagination" in data
        assert isinstance(data["events"], list)
        assert len(data["events"]) >= 1
        
        # Check event structure
        event = data["events"][0]
        assert "id" in event
        assert "title" in event
        assert "description" in event
        assert "category" in event
        assert "organizer" in event
        assert "date" in event
        assert "startTime" in event
        assert "endTime" in event
        assert "venue" in event
        assert "capacity" in event
        assert "registeredCount" in event
        assert "status" in event
    
    def test_get_events_only_published(self, client, sample_student, db, sample_category, sample_organizer):
        """Test that only published events are returned."""
        # Create published event
        published_event = Event(
            id=str(uuid.uuid4()),
            title="Published Event",
            description="This is a published event with enough description to pass validation.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(published_event)
        
        # Create draft event
        draft_event = Event(
            id=str(uuid.uuid4()),
            title="Draft Event",
            description="This is a draft event with enough description to pass validation.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(14, 0),
            end_time=time(16, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.DRAFT
        )
        db.add(draft_event)
        
        # Create pending event
        pending_event = Event(
            id=str(uuid.uuid4()),
            title="Pending Event",
            description="This is a pending event with enough description to pass validation.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(18, 0),
            end_time=time(20, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.PENDING
        )
        db.add(pending_event)
        db.commit()
        
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/events",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        event_titles = [e["title"] for e in data["events"]]
        assert "Published Event" in event_titles
        assert "Draft Event" not in event_titles
        assert "Pending Event" not in event_titles
    
    def test_get_events_pagination(self, client, sample_student, db, sample_category, sample_organizer):
        """Test pagination functionality."""
        # Create multiple events
        for i in range(25):
            event = Event(
                id=str(uuid.uuid4()),
                title=f"Event {i+1}",
                description=f"This is event {i+1} with enough description to pass validation.",
                category_id=sample_category.id,
                organizer_id=sample_organizer.id,
                date=date.today() + timedelta(days=i+1),
                start_time=time(10, 0),
                end_time=time(12, 0),
                venue="Test Venue",
                location="Test Location",
                capacity=100,
                status=EventStatus.PUBLISHED,
                published_at=datetime.now()
            )
            db.add(event)
        db.commit()
        
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Get first page
        response = client.get(
            "/api/events?page=1&limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["events"]) == 10
        assert data["pagination"]["currentPage"] == 1
        assert data["pagination"]["itemsPerPage"] == 10
        assert data["pagination"]["totalItems"] >= 25
        assert data["pagination"]["totalPages"] >= 3
        
        # Get second page
        response = client.get(
            "/api/events?page=2&limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["events"]) == 10
        assert data["pagination"]["currentPage"] == 2
    
    def test_get_events_filter_by_category(self, client, sample_student, db, sample_category, sample_organizer):
        """Test filtering events by category."""
        # Create another category
        other_category = Category(
            id=str(uuid.uuid4()),
            name="Other Category",
            slug="other-category",
            color="green",
            is_active=True
        )
        db.add(other_category)
        
        # Create event in sample category
        event1 = Event(
            id=str(uuid.uuid4()),
            title="Event in Sample Category",
            description="This is an event in the sample category with enough description.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event1)
        
        # Create event in other category
        event2 = Event(
            id=str(uuid.uuid4()),
            title="Event in Other Category",
            description="This is an event in the other category with enough description.",
            category_id=other_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(14, 0),
            end_time=time(16, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event2)
        db.commit()
        
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Filter by sample category slug
        response = client.get(
            f"/api/events?category={sample_category.slug}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        event_titles = [e["title"] for e in data["events"]]
        assert "Event in Sample Category" in event_titles
        assert "Event in Other Category" not in event_titles
    
    def test_get_events_filter_by_category_not_found(self, client, sample_student):
        """Test filtering by non-existent category."""
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/events?category=nonexistent-category",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_events_search(self, client, sample_student, db, sample_category, sample_organizer):
        """Test searching events by title."""
        # Create events with different titles
        event1 = Event(
            id=str(uuid.uuid4()),
            title="Basketball Tournament",
            description="This is a basketball tournament with enough description to pass validation.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event1)
        
        event2 = Event(
            id=str(uuid.uuid4()),
            title="Career Fair",
            description="This is a career fair with enough description to pass validation.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(14, 0),
            end_time=time(16, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event2)
        db.commit()
        
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Search for basketball
        response = client.get(
            "/api/events?search=basketball",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        event_titles = [e["title"] for e in data["events"]]
        assert "Basketball Tournament" in event_titles
        assert "Career Fair" not in event_titles
    
    def test_get_events_filter_by_date_range(self, client, sample_student, db, sample_category, sample_organizer):
        """Test filtering events by date range."""
        today = date.today()
        
        # Create event in date range
        event1 = Event(
            id=str(uuid.uuid4()),
            title="Event in Range",
            description="This is an event in the date range with enough description.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=today + timedelta(days=5),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event1)
        
        # Create event outside date range
        event2 = Event(
            id=str(uuid.uuid4()),
            title="Event Outside Range",
            description="This is an event outside the date range with enough description.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=today + timedelta(days=20),
            start_time=time(14, 0),
            end_time=time(16, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event2)
        db.commit()
        
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Filter by date range
        start_date = (today + timedelta(days=1)).isoformat()
        end_date = (today + timedelta(days=10)).isoformat()
        response = client.get(
            f"/api/events?startDate={start_date}&endDate={end_date}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        event_titles = [e["title"] for e in data["events"]]
        assert "Event in Range" in event_titles
        assert "Event Outside Range" not in event_titles
    
    def test_get_events_filter_by_availability(self, client, sample_student, db, sample_category, sample_organizer):
        """Test filtering events by availability."""
        # Create event with available spots
        event1 = Event(
            id=str(uuid.uuid4()),
            title="Available Event",
            description="This is an event with available spots with enough description.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            registered_count=50,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event1)
        
        # Create event that's full
        event2 = Event(
            id=str(uuid.uuid4()),
            title="Full Event",
            description="This is a full event with enough description.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(14, 0),
            end_time=time(16, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            registered_count=100,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event2)
        db.commit()
        
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Filter by availability
        response = client.get(
            "/api/events?availability=true",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        event_titles = [e["title"] for e in data["events"]]
        assert "Available Event" in event_titles
        assert "Full Event" not in event_titles
    
    def test_get_events_sort_by_title(self, client, sample_student, db, sample_category, sample_organizer):
        """Test sorting events by title."""
        # Create events with different titles
        event1 = Event(
            id=str(uuid.uuid4()),
            title="Zebra Event",
            description="This is a zebra event with enough description.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event1)
        
        event2 = Event(
            id=str(uuid.uuid4()),
            title="Alpha Event",
            description="This is an alpha event with enough description.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(14, 0),
            end_time=time(16, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event2)
        db.commit()
        
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Sort by title
        response = client.get(
            "/api/events?sortBy=title",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        event_titles = [e["title"] for e in data["events"]]
        # Check that events are sorted alphabetically
        assert event_titles == sorted(event_titles)
    
    def test_get_events_invalid_sort_by(self, client, sample_student):
        """Test invalid sortBy parameter."""
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/events?sortBy=invalid",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_events_invalid_date_format(self, client, sample_student):
        """Test invalid date format."""
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/events?startDate=invalid-date",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_events_invalid_page_number(self, client, sample_student):
        """Test invalid page number."""
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/events?page=0",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_events_invalid_limit(self, client, sample_student):
        """Test invalid limit."""
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/events?limit=101",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_events_requires_authentication(self, client):
        """Test that events endpoint requires authentication."""
        response = client.get("/api/events")
        
        # Should require authentication
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


# =============================================================================
# TEST: Get Event Detail (GET /api/events/{id})
# =============================================================================
class TestGetEventDetail:
    """Test event detail endpoint."""
    
    def test_get_event_detail_success(self, client, sample_published_event):
        """Test successful retrieval of event details."""
        response = client.get(f"/api/events/{sample_published_event.id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "event" in data
        
        event = data["event"]
        assert event["id"] == sample_published_event.id
        assert event["title"] == sample_published_event.title
        assert event["description"] == sample_published_event.description
        assert "category" in event
        assert "organizer" in event
        assert "remainingCapacity" in event
        assert event["remainingCapacity"] == (event["capacity"] - event["registeredCount"])
    
    def test_get_event_detail_not_found(self, client):
        """Test getting non-existent event."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/events/{fake_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_get_event_detail_draft_not_visible(self, client, db, sample_category, sample_organizer):
        """Test that draft events are not visible."""
        draft_event = Event(
            id=str(uuid.uuid4()),
            title="Draft Event",
            description="This is a draft event with enough description to pass validation.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.DRAFT
        )
        db.add(draft_event)
        db.commit()
        
        response = client.get(f"/api/events/{draft_event.id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_event_detail_pending_not_visible(self, client, db, sample_category, sample_organizer):
        """Test that pending events are not visible."""
        pending_event = Event(
            id=str(uuid.uuid4()),
            title="Pending Event",
            description="This is a pending event with enough description to pass validation.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.PENDING
        )
        db.add(pending_event)
        db.commit()
        
        response = client.get(f"/api/events/{pending_event.id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_event_detail_invalid_id_format(self, client):
        """Test getting event with invalid ID format."""
        response = client.get("/api/events/invalid-id-format")
        
        # Should return 404 (not found) rather than validation error
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_event_detail_remaining_capacity_calculation(self, client, db, sample_category, sample_organizer):
        """Test that remaining capacity is calculated correctly."""
        event = Event(
            id=str(uuid.uuid4()),
            title="Capacity Test Event",
            description="This is a test event with enough description to pass validation.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            registered_count=30,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event)
        db.commit()
        
        response = client.get(f"/api/events/{event.id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        event_data = data["event"]
        assert event_data["remainingCapacity"] == 70
        assert event_data["capacity"] == 100
        assert event_data["registeredCount"] == 30


# =============================================================================
# TEST: Edge Cases and Integration
# =============================================================================
class TestEventEdgeCases:
    """Test edge cases and integration scenarios."""
    
    def test_get_events_empty_result(self, client, sample_student, db):
        """Test getting events when no published events exist."""
        # Clear all events
        db.query(Event).delete()
        db.commit()
        
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        response = client.get(
            "/api/events",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["events"] == []
        assert data["pagination"]["totalItems"] == 0
    
    def test_get_events_multiple_filters(self, client, sample_student, db, sample_category, sample_organizer):
        """Test combining multiple filters."""
        today = date.today()
        
        # Create event matching all filters
        matching_event = Event(
            id=str(uuid.uuid4()),
            title="Matching Event",
            description="This is a matching event with enough description.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=today + timedelta(days=5),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            registered_count=50,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(matching_event)
        db.commit()
        
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Apply multiple filters
        start_date = (today + timedelta(days=1)).isoformat()
        end_date = (today + timedelta(days=10)).isoformat()
        response = client.get(
            f"/api/events?category={sample_category.slug}&startDate={start_date}&endDate={end_date}&availability=true",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        event_titles = [e["title"] for e in data["events"]]
        assert "Matching Event" in event_titles
    
    def test_get_events_case_insensitive_search(self, client, sample_student, db, sample_category, sample_organizer):
        """Test that search is case insensitive."""
        event = Event(
            id=str(uuid.uuid4()),
            title="Basketball Championship",
            description="This is a basketball championship with enough description.",
            category_id=sample_category.id,
            organizer_id=sample_organizer.id,
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            end_time=time(12, 0),
            venue="Test Venue",
            location="Test Location",
            capacity=100,
            status=EventStatus.PUBLISHED,
            published_at=datetime.now()
        )
        db.add(event)
        db.commit()
        
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "teststudent@umd.edu",
                "password": "password123"
            }
        )
        token = login_response.json()["token"]
        
        # Search with different cases
        response = client.get(
            "/api/events?search=BASKETBALL",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        event_titles = [e["title"] for e in data["events"]]
        assert "Basketball Championship" in event_titles
