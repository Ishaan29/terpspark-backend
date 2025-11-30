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


@pytest.fixture(autouse=True)
def mock_email_service():
    """Mock email service to avoid actual email sending."""
    with patch('app.services.registration_service.EmailService') as mock_email:
        # Create a mock instance
        mock_instance = Mock()
        mock_instance.send_registration_confirmation.return_value = True
        mock_instance.send_cancellation_confirmation.return_value = True
        mock_instance.send_waitlist_confirmation.return_value = True
        mock_instance.send_waitlist_promotion.return_value = True
        mock_email.return_value = mock_instance
        yield mock_instance
