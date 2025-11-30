"""
Pytest configuration file.
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.venue import Venue
from app.models.event import Event, EventStatus
from app.models.registration import Registration, RegistrationStatus, CheckInStatus
from app.models.waitlist import WaitlistEntry, NotificationPreference
from app.models.organizer_approval import OrganizerApprovalRequest, ApprovalStatus
from app.models.audit_log import AuditLog, AuditAction, TargetType
from app.core.security import get_password_hash
from main import app
from datetime import date, time, datetime, timedelta
import uuid

# Use in-memory SQLite for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create test client."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_student(db):
    """Create a sample student user."""
    user = User(
        id=str(uuid.uuid4()),
        email="teststudent@umd.edu",
        password=get_password_hash("password123"),
        name="Test Student",
        role=UserRole.STUDENT,
        is_approved=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_organizer(db):
    """Create a sample approved organizer."""
    user = User(
        id=str(uuid.uuid4()),
        email="testorganizer@umd.edu",
        password=get_password_hash("password123"),
        name="Test Organizer",
        role=UserRole.ORGANIZER,
        is_approved=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_pending_organizer(db):
    """Create a sample pending (not approved) organizer."""
    user = User(
        id=str(uuid.uuid4()),
        email="pendingorganizer@umd.edu",
        password=get_password_hash("password123"),
        name="Pending Organizer",
        role=UserRole.ORGANIZER,
        is_approved=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_other_organizer(db):
    """Create another sample approved organizer for ownership tests."""
    user = User(
        id=str(uuid.uuid4()),
        email="otherorganizer@umd.edu",
        password=get_password_hash("password123"),
        name="Other Organizer",
        role=UserRole.ORGANIZER,
        is_approved=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_admin(db):
    """Create a sample admin user."""
    user = User(
        id=str(uuid.uuid4()),
        email="testadmin@umd.edu",
        password=get_password_hash("password123"),
        name="Test Admin",
        role=UserRole.ADMIN,
        is_approved=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_category(db):
    """Create a sample category."""
    category = Category(
        id=str(uuid.uuid4()),
        name="Test Category",
        slug="test-category",
        description="A test category",
        color="blue",
        icon="test-icon",
        is_active=True
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture
def sample_venue(db):
    """Create a sample venue."""
    venue = Venue(
        id=str(uuid.uuid4()),
        name="Test Venue",
        building="Test Building",
        capacity=100,
        facilities=["Projector", "WiFi"],
        is_active=True
    )
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return venue


@pytest.fixture
def sample_published_event(db, sample_category, sample_organizer):
    """Create a sample published event."""
    event = Event(
        id=str(uuid.uuid4()),
        title="Test Published Event",
        description="This is a test published event with enough description to pass validation requirements.",
        category_id=sample_category.id,
        organizer_id=sample_organizer.id,
        date=date.today() + timedelta(days=7),
        start_time=time(10, 0),
        end_time=time(12, 0),
        venue="Test Venue",
        location="Test Location, Room 101",
        capacity=100,
        registered_count=0,
        waitlist_count=0,
        status=EventStatus.PUBLISHED,
        published_at=datetime.now()
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture
def sample_full_event(db, sample_category, sample_organizer):
    """Create a sample published event that is full."""
    event = Event(
        id=str(uuid.uuid4()),
        title="Test Full Event",
        description="This is a test published event that is at capacity.",
        category_id=sample_category.id,
        organizer_id=sample_organizer.id,
        date=date.today() + timedelta(days=7),
        start_time=time(10, 0),
        end_time=time(12, 0),
        venue="Test Venue",
        location="Test Location, Room 101",
        capacity=10,
        registered_count=10,  # Full
        waitlist_count=0,
        status=EventStatus.PUBLISHED,
        published_at=datetime.now()
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture
def sample_draft_event(db, sample_category, sample_organizer):
    """Create a sample draft event."""
    event = Event(
        id=str(uuid.uuid4()),
        title="Test Draft Event",
        description="This is a test draft event with enough description to pass validation requirements.",
        category_id=sample_category.id,
        organizer_id=sample_organizer.id,
        date=date.today() + timedelta(days=7),
        start_time=time(10, 0),
        end_time=time(12, 0),
        venue="Test Venue",
        location="Test Location, Room 101",
        capacity=100,
        registered_count=0,
        waitlist_count=0,
        status=EventStatus.DRAFT
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture
def sample_cancelled_event(db, sample_category, sample_organizer):
    """Create a sample cancelled event."""
    event = Event(
        id=str(uuid.uuid4()),
        title="Test Cancelled Event",
        description="This is a test cancelled event with enough description to pass validation requirements.",
        category_id=sample_category.id,
        organizer_id=sample_organizer.id,
        date=date.today() + timedelta(days=7),
        start_time=time(10, 0),
        end_time=time(12, 0),
        venue="Test Venue",
        location="Test Location, Room 101",
        capacity=100,
        registered_count=0,
        waitlist_count=0,
        status=EventStatus.CANCELLED,
        cancelled_at=datetime.now()
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture
def sample_registration(db, sample_student, sample_published_event):
    """Create a sample registration."""
    registration = Registration(
        id=str(uuid.uuid4()),
        user_id=sample_student.id,
        event_id=sample_published_event.id,
        status=RegistrationStatus.CONFIRMED,
        ticket_code="TKT-TEST-123",
        qr_code="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        check_in_status=CheckInStatus.NOT_CHECKED_IN,
        guests=None,
        sessions=None,
        reminder_sent=False
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


@pytest.fixture
def sample_waitlist_entry(db, sample_student, sample_full_event):
    """Create a sample waitlist entry."""
    waitlist_entry = WaitlistEntry(
        id=str(uuid.uuid4()),
        user_id=sample_student.id,
        event_id=sample_full_event.id,
        position=1,
        notification_preference=NotificationPreference.EMAIL
    )
    db.add(waitlist_entry)
    db.commit()
    db.refresh(waitlist_entry)
    return waitlist_entry


@pytest.fixture
def sample_checked_in_registration(db, sample_student, sample_published_event):
    """Create a sample checked-in registration."""
    registration = Registration(
        id=str(uuid.uuid4()),
        user_id=sample_student.id,
        event_id=sample_published_event.id,
        status=RegistrationStatus.CONFIRMED,
        ticket_code="TKT-CHECKED-123",
        qr_code="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        check_in_status=CheckInStatus.CHECKED_IN,
        checked_in_at=datetime.now(),
        guests=None,
        sessions=None,
        reminder_sent=False
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


@pytest.fixture
def sample_pending_event(db, sample_category, sample_organizer):
    """Create a sample pending event."""
    event = Event(
        id=str(uuid.uuid4()),
        title="Test Pending Event",
        description="This is a test pending event with enough description to pass validation requirements.",
        category_id=sample_category.id,
        organizer_id=sample_organizer.id,
        date=date.today() + timedelta(days=7),
        start_time=time(10, 0),
        end_time=time(12, 0),
        venue="Test Venue",
        location="Test Location, Room 101",
        capacity=100,
        registered_count=0,
        waitlist_count=0,
        status=EventStatus.PENDING
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture
def sample_organizer_approval_request(db, sample_pending_organizer):
    """Create a sample organizer approval request."""
    approval_request = OrganizerApprovalRequest(
        id=str(uuid.uuid4()),
        user_id=sample_pending_organizer.id,
        reason="I want to organize events for the university community and help students connect.",
        status=ApprovalStatus.PENDING,
        requested_at=datetime.now()
    )
    db.add(approval_request)
    db.commit()
    db.refresh(approval_request)
    return approval_request


@pytest.fixture
def sample_inactive_category(db):
    """Create a sample inactive category."""
    category = Category(
        id=str(uuid.uuid4()),
        name="Inactive Category",
        slug="inactive-category",
        description="An inactive test category",
        color="gray",
        icon="inactive-icon",
        is_active=False
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture
def sample_inactive_venue(db):
    """Create a sample inactive venue."""
    venue = Venue(
        id=str(uuid.uuid4()),
        name="Inactive Venue",
        building="Inactive Building",
        capacity=50,
        facilities=[],
        is_active=False
    )
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return venue


@pytest.fixture(autouse=True)
def mock_email_service():
    """Mock email service to avoid actual email sending."""
    with patch('app.services.registration_service.EmailService') as mock_reg_email, \
         patch('app.services.organizer_service.EmailService') as mock_org_email, \
         patch('app.services.admin_service.EmailService') as mock_admin_email:
        # Create a mock instance
        mock_instance = Mock()
        mock_instance.send_registration_confirmation.return_value = True
        mock_instance.send_cancellation_confirmation.return_value = True
        mock_instance.send_waitlist_confirmation.return_value = True
        mock_instance.send_waitlist_promotion.return_value = True
        mock_instance.send_announcement.return_value = {"recipientCount": 1}
        mock_instance.send_organizer_approval.return_value = True
        mock_instance.send_organizer_rejection.return_value = True
        mock_instance.send_event_approval.return_value = True
        mock_instance.send_event_rejection.return_value = True
        mock_reg_email.return_value = mock_instance
        mock_org_email.return_value = mock_instance
        mock_admin_email.return_value = mock_instance
        yield mock_instance
