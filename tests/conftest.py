"""
Pytest configuration file.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.venue import Venue
from app.models.event import Event, EventStatus
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
