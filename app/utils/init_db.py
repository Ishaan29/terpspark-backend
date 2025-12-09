import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, init_db
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.venue import Venue
from app.models.event import Event, EventStatus
from app.models.registration import Registration, RegistrationStatus, CheckInStatus
from app.models.waitlist import WaitlistEntry, NotificationPreference
from app.models.organizer_approval import OrganizerApprovalRequest, ApprovalStatus
from app.models.audit_log import AuditLog, AuditAction, TargetType
from app.core.security import get_password_hash
from datetime import datetime, date, time, timedelta
import uuid


def create_sample_users(db):
    print("\n👥 Creating sample users...")
    
    users = []
    
    # Admin user
    admin = User(
        id=str(uuid.uuid4()),
        email="admin@umd.edu",
        password=get_password_hash("admin123"),
        name="Admin User",
        role=UserRole.ADMIN,
        is_approved=True,
        department="Computer Science"
    )
    db.add(admin)
    users.append(admin)
    print(f"✅ Created admin: admin@umd.edu / admin123")
    
    # Approved organizers
    organizers = [
        {
            "email": "organizer@umd.edu",
            "name": "Sarah Johnson",
            "department": "Student Affairs"
        },
        {
            "email": "techclub@umd.edu",
            "name": "Tech Club Organizer",
            "department": "Computer Science"
        },
        {
            "email": "sportsclub@umd.edu",
            "name": "Sports Events Team",
            "department": "Athletics"
        },
        {
            "email": "artscenter@umd.edu",
            "name": "Arts Center",
            "department": "Fine Arts"
        }
    ]
    
    for org_data in organizers:
        organizer = User(
            id=str(uuid.uuid4()),
            email=org_data["email"],
            password=get_password_hash("organizer123"),
            name=org_data["name"],
            role=UserRole.ORGANIZER,
            is_approved=True,
            department=org_data["department"]
        )
        db.add(organizer)
        users.append(organizer)
        print(f"✅ Created organizer: {org_data['email']} / organizer123")
    
    # Pending organizer (not approved)
    pending_organizer = User(
        id=str(uuid.uuid4()),
        email="pending@umd.edu",
        password=get_password_hash("pending123"),
        name="Pending Organizer",
        role=UserRole.ORGANIZER,
        is_approved=False,
        department="Student Activities"
    )
    db.add(pending_organizer)
    users.append(pending_organizer)
    print(f"✅ Created pending organizer: pending@umd.edu / pending123")
    
    # Student users
    students = [
        {
            "email": "student@umd.edu",
            "name": "John Student",
            "department": "Engineering",
            "grad_year": "2026"
        },
        {
            "email": "jane.smith@umd.edu",
            "name": "Jane Smith",
            "department": "Business",
            "grad_year": "2025"
        },
        {
            "email": "mike.wilson@umd.edu",
            "name": "Mike Wilson",
            "department": "Computer Science",
            "grad_year": "2026"
        },
        {
            "email": "emily.brown@umd.edu",
            "name": "Emily Brown",
            "department": "Biology",
            "grad_year": "2027"
        },
        {
            "email": "alex.davis@umd.edu",
            "name": "Alex Davis",
            "department": "Mathematics",
            "grad_year": "2025"
        }
    ]
    
    for student_data in students:
        student = User(
            id=str(uuid.uuid4()),
            email=student_data["email"],
            password=get_password_hash("student123"),
            name=student_data["name"],
            role=UserRole.STUDENT,
            is_approved=True,
            department=student_data["department"],
            graduation_year=student_data["grad_year"]
        )
        db.add(student)
        users.append(student)
        print(f"✅ Created student: {student_data['email']} / student123")
    
    db.commit()
    return users


def create_sample_categories(db):
    """Create predefined event categories."""
    print("\n📁 Creating event categories...")
    
    categories_data = [
        {
            "name": "Academic",
            "slug": "academic",
            "color": "blue",
            "icon": "📚",
            "description": "Academic events, workshops, and lectures"
        },
        {
            "name": "Career",
            "slug": "career",
            "color": "green",
            "icon": "💼",
            "description": "Career fairs, networking events, and job opportunities"
        },
        {
            "name": "Cultural",
            "slug": "cultural",
            "color": "purple",
            "icon": "🌍",
            "description": "Cultural celebrations and multicultural events"
        },
        {
            "name": "Sports",
            "slug": "sports",
            "color": "red",
            "icon": "⚽",
            "description": "Sports events, tournaments, and fitness activities"
        },
        {
            "name": "Arts",
            "slug": "arts",
            "color": "pink",
            "icon": "🎨",
            "description": "Art exhibitions, performances, and creative workshops"
        },
        {
            "name": "Technology",
            "slug": "technology",
            "color": "indigo",
            "icon": "💻",
            "description": "Tech talks, hackathons, and innovation events"
        },
        {
            "name": "Wellness",
            "slug": "wellness",
            "color": "teal",
            "icon": "🧘",
            "description": "Health, wellness, and mindfulness events"
        },
        {
            "name": "Environmental",
            "slug": "environmental",
            "color": "emerald",
            "icon": "🌱",
            "description": "Environmental awareness and sustainability events"
        }
    ]
    
    categories = []
    for cat_data in categories_data:
        category = Category(
            id=str(uuid.uuid4()),
            name=cat_data["name"],
            slug=cat_data["slug"],
            color=cat_data["color"],
            icon=cat_data["icon"],
            description=cat_data["description"],
            is_active=True
        )
        db.add(category)
        categories.append(category)
        print(f"✅ Created category: {cat_data['name']}")
    
    db.commit()
    return categories


def create_sample_venues(db):
    """Create sample venues."""
    print("\n🏛️ Creating venues...")
    
    venues_data = [
        {
            "name": "Grand Ballroom",
            "building": "Stamp Student Union",
            "capacity": 500,
            "facilities": ["Projector", "Sound System", "WiFi", "Stage", "Microphones"]
        },
        {
            "name": "Auditorium",
            "building": "Edward St. John Learning & Teaching Center",
            "capacity": 300,
            "facilities": ["Projector", "Sound System", "WiFi", "Recording Equipment"]
        },
        {
            "name": "Conference Room A",
            "building": "Stamp Student Union",
            "capacity": 50,
            "facilities": ["Projector", "WiFi", "Whiteboard", "Conference Table"]
        },
        {
            "name": "Outdoor Amphitheater",
            "building": "Campus Drive",
            "capacity": 1000,
            "facilities": ["Sound System", "Stage", "Outdoor Seating"]
        },
        {
            "name": "McKeldin Library - Room 6137",
            "building": "McKeldin Library",
            "capacity": 100,
            "facilities": ["Projector", "WiFi", "Whiteboard"]
        },
        {
            "name": "Eppley Recreation Center - Gymnasium",
            "building": "Eppley Recreation Center",
            "capacity": 200,
            "facilities": ["Sound System", "Scoreboard", "Bleachers"]
        },
        {
            "name": "Engineering Classroom Building - Room 1180",
            "building": "Engineering Classroom Building",
            "capacity": 150,
            "facilities": ["Projector", "WiFi", "Recording Equipment", "Lab Equipment"]
        },
        {
            "name": "Art-Sociology Building - Gallery",
            "building": "Art-Sociology Building",
            "capacity": 75,
            "facilities": ["Gallery Lighting", "Display Walls", "WiFi"]
        }
    ]
    
    venues = []
    for venue_data in venues_data:
        venue = Venue(
            id=str(uuid.uuid4()),
            name=venue_data["name"],
            building=venue_data["building"],
            capacity=venue_data["capacity"],
            facilities=venue_data["facilities"],
            is_active=True
        )
        db.add(venue)
        venues.append(venue)
        print(f"✅ Created venue: {venue_data['name']}")
    
    db.commit()
    return venues


def create_sample_events(db, organizers, categories):
    """Create sample events with different statuses."""
    print("\n📅 Creating events...")
    
    today = date.today()
    events = []
    
    # Published Events (upcoming)
    published_events = [
        {
            "title": "AI & Machine Learning Workshop",
            "description": "Join us for an intensive hands-on workshop covering the fundamentals of AI and Machine Learning. Learn about neural networks, deep learning, and practical applications. Perfect for students interested in cutting-edge technology. Bring your laptop!",
            "category": "Technology",
            "organizer": "techclub@umd.edu",
            "date": today + timedelta(days=7),
            "start_time": "14:00",
            "end_time": "17:00",
            "venue": "Engineering Classroom Building - Room 1180",
            "location": "Engineering Classroom Building, Room 1180, UMD Campus",
            "capacity": 100,
            "registered_count": 75,
            "tags": ["AI", "Machine Learning", "Workshop", "Technology"],
            "is_featured": True
        },
        {
            "title": "Spring Career Fair 2025",
            "description": "Meet with top employers from various industries! This career fair features over 100 companies looking to hire UMD students for internships and full-time positions. Dress professionally and bring multiple copies of your resume. Networking sessions throughout the day.",
            "category": "Career",
            "organizer": "organizer@umd.edu",
            "date": today + timedelta(days=14),
            "start_time": "10:00",
            "end_time": "16:00",
            "venue": "Grand Ballroom",
            "location": "Stamp Student Union, Grand Ballroom",
            "capacity": 500,
            "registered_count": 450,
            "tags": ["Career", "Job Fair", "Networking", "Professional Development"],
            "is_featured": True
        },
        {
            "title": "International Food Festival",
            "description": "Celebrate diversity at our annual International Food Festival! Sample cuisines from around the world, enjoy cultural performances, and learn about different traditions. All food prepared by international student organizations. Free entry!",
            "category": "Cultural",
            "organizer": "organizer@umd.edu",
            "date": today + timedelta(days=21),
            "start_time": "12:00",
            "end_time": "18:00",
            "venue": "Outdoor Amphitheater",
            "location": "Campus Drive, Outdoor Amphitheater",
            "capacity": 1000,
            "registered_count": 350,
            "tags": ["Cultural", "Food", "Festival", "International"],
            "is_featured": True
        },
        {
            "title": "Basketball Tournament Finals",
            "description": "Cheer for your favorite teams in the intramural basketball tournament finals! The top four teams compete for the championship trophy. Refreshments will be available. Free t-shirts for the first 100 attendees!",
            "category": "Sports",
            "organizer": "sportsclub@umd.edu",
            "date": today + timedelta(days=10),
            "start_time": "18:00",
            "end_time": "21:00",
            "venue": "Eppley Recreation Center - Gymnasium",
            "location": "Eppley Recreation Center, Main Gymnasium",
            "capacity": 200,
            "registered_count": 180,
            "tags": ["Sports", "Basketball", "Tournament", "Competition"],
            "is_featured": False
        },
        {
            "title": "Mindfulness & Meditation Session",
            "description": "Take a break from your busy schedule and join us for a calming meditation session. Learn mindfulness techniques to manage stress, improve focus, and enhance overall well-being. Suitable for beginners. Yoga mats provided.",
            "category": "Wellness",
            "organizer": "organizer@umd.edu",
            "date": today + timedelta(days=5),
            "start_time": "17:00",
            "end_time": "18:30",
            "venue": "Conference Room A",
            "location": "Stamp Student Union, Conference Room A",
            "capacity": 50,
            "registered_count": 45,
            "tags": ["Wellness", "Meditation", "Mindfulness", "Health"],
            "is_featured": False
        },
        {
            "title": "Student Art Exhibition Opening",
            "description": "Celebrate student creativity at our annual art exhibition! View stunning works across various mediums including painting, sculpture, photography, and digital art. Meet the artists and enjoy complimentary refreshments.",
            "category": "Arts",
            "organizer": "artscenter@umd.edu",
            "date": today + timedelta(days=12),
            "start_time": "18:00",
            "end_time": "20:00",
            "venue": "Art-Sociology Building - Gallery",
            "location": "Art-Sociology Building, Main Gallery",
            "capacity": 75,
            "registered_count": 40,
            "tags": ["Arts", "Exhibition", "Student Work", "Gallery"],
            "is_featured": False
        },
        {
            "title": "Campus Sustainability Workshop",
            "description": "Learn how to reduce your environmental footprint! This workshop covers sustainable living practices, recycling programs on campus, and ways to get involved in environmental initiatives. Take home a free reusable water bottle!",
            "category": "Environmental",
            "organizer": "organizer@umd.edu",
            "date": today + timedelta(days=18),
            "start_time": "15:00",
            "end_time": "17:00",
            "venue": "McKeldin Library - Room 6137",
            "location": "McKeldin Library, Room 6137",
            "capacity": 100,
            "registered_count": 55,
            "tags": ["Environmental", "Sustainability", "Workshop", "Green Living"],
            "is_featured": False
        },
        {
            "title": "Research Methods in Data Science",
            "description": "An academic seminar exploring advanced research methodologies in data science. Topics include experimental design, statistical analysis, and reproducible research practices. Recommended for graduate students and advanced undergraduates.",
            "category": "Academic",
            "organizer": "techclub@umd.edu",
            "date": today + timedelta(days=9),
            "start_time": "13:00",
            "end_time": "15:00",
            "venue": "Engineering Classroom Building - Room 1180",
            "location": "Engineering Classroom Building, Room 1180",
            "capacity": 80,
            "registered_count": 50,
            "tags": ["Academic", "Research", "Data Science", "Seminar"],
            "is_featured": False
        }
    ]
    
    # Create published events
    for event_data in published_events:
        category = next(c for c in categories if c.name == event_data["category"])
        organizer = next(o for o in organizers if o.email == event_data["organizer"])
        
        start_hour, start_min = map(int, event_data["start_time"].split(":"))
        end_hour, end_min = map(int, event_data["end_time"].split(":"))
        
        event = Event(
            id=str(uuid.uuid4()),
            title=event_data["title"],
            description=event_data["description"],
            category_id=category.id,
            organizer_id=organizer.id,
            date=event_data["date"],
            start_time=time(start_hour, start_min),
            end_time=time(end_hour, end_min),
            venue=event_data["venue"],
            location=event_data["location"],
            capacity=event_data["capacity"],
            registered_count=event_data["registered_count"],
            waitlist_count=0,
            status=EventStatus.PUBLISHED,
            tags=event_data["tags"],
            is_featured=event_data["is_featured"],
            published_at=datetime.utcnow() - timedelta(days=3)
        )
        db.add(event)
        events.append(event)
        print(f"✅ Created published event: {event_data['title']}")
    
    # Pending Events (awaiting approval)
    pending_events = [
        {
            "title": "Hackathon 2025",
            "description": "Join us for a 24-hour coding marathon! Build innovative solutions, network with fellow developers, and compete for amazing prizes. All skill levels welcome. Food and drinks provided throughout the event.",
            "category": "Technology",
            "organizer": "techclub@umd.edu",
            "date": today + timedelta(days=30),
            "start_time": "09:00",
            "end_time": "09:00",
            "venue": "Grand Ballroom",
            "location": "Stamp Student Union, Grand Ballroom",
            "capacity": 200,
            "tags": ["Hackathon", "Coding", "Technology", "Competition"]
        },
        {
            "title": "Mental Health Awareness Week",
            "description": "A week-long series of events focused on mental health awareness, including workshops, panel discussions, and support groups. Learn about resources available on campus and how to support friends in need.",
            "category": "Wellness",
            "organizer": "organizer@umd.edu",
            "date": today + timedelta(days=25),
            "start_time": "10:00",
            "end_time": "16:00",
            "venue": "Auditorium",
            "location": "Edward St. John Learning & Teaching Center, Auditorium",
            "capacity": 300,
            "tags": ["Wellness", "Mental Health", "Awareness", "Support"]
        }
    ]
    
    for event_data in pending_events:
        category = next(c for c in categories if c.name == event_data["category"])
        organizer = next(o for o in organizers if o.email == event_data["organizer"])
        
        start_hour, start_min = map(int, event_data["start_time"].split(":"))
        end_hour, end_min = map(int, event_data["end_time"].split(":"))
        
        event = Event(
            id=str(uuid.uuid4()),
            title=event_data["title"],
            description=event_data["description"],
            category_id=category.id,
            organizer_id=organizer.id,
            date=event_data["date"],
            start_time=time(start_hour, start_min),
            end_time=time(end_hour, end_min),
            venue=event_data["venue"],
            location=event_data["location"],
            capacity=event_data["capacity"],
            registered_count=0,
            waitlist_count=0,
            status=EventStatus.PENDING,
            tags=event_data["tags"],
            is_featured=False
        )
        db.add(event)
        events.append(event)
        print(f"✅ Created pending event: {event_data['title']}")
    
    db.commit()
    return events


def initialize_all_data():
    """Initialize all sample data."""
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_user = db.query(User).first()
        if existing_user:
            print("⚠️  Data already exists. Skipping sample data creation.")
            print("   To recreate data, drop all tables and run this script again.")
            return
        
        print("🚀 Initializing sample data for all models...")
        
        # Create data in order of dependencies
        users = create_sample_users(db)
        categories = create_sample_categories(db)
        venues = create_sample_venues(db)
        
        # Separate users by role
        admin = next(u for u in users if u.role == UserRole.ADMIN)
        organizers = [u for u in users if u.role == UserRole.ORGANIZER and u.is_approved]
        pending_organizer = next(u for u in users if u.role == UserRole.ORGANIZER and not u.is_approved)
        students = [u for u in users if u.role == UserRole.STUDENT]
        
        events = create_sample_events(db, organizers, categories)
        
        print("\n✨ All sample data created successfully!")
        print("\n" + "="*60)
        print("📋 SUMMARY")
        print("="*60)
        print(f"👥 Users: {len(users)}")
        print(f"   - Admins: 1")
        print(f"   - Organizers: {len(organizers)}")
        print(f"   - Pending Organizers: 1")
        print(f"   - Students: {len(students)}")
        print(f"📁 Categories: {len(categories)}")
        print(f"🏛️  Venues: {len(venues)}")
        print(f"📅 Events: {len(events)}")
        print(f"   - Published: {len([e for e in events if e.status == EventStatus.PUBLISHED])}")
        print(f"   - Pending: {len([e for e in events if e.status == EventStatus.PENDING])}")
        print("="*60)
        
        print("\n🔐 LOGIN CREDENTIALS:")
        print("-" * 60)
        print("Admin:")
        print("  Email: admin@umd.edu")
        print("  Password: admin123")
        print("\nOrganizers:")
        print("  Email: organizer@umd.edu / Password: organizer123")
        print("  Email: techclub@umd.edu / Password: organizer123")
        print("  Email: sportsclub@umd.edu / Password: organizer123")
        print("  Email: artscenter@umd.edu / Password: organizer123")
        print("\nStudents:")
        print("  Email: student@umd.edu / Password: student123")
        print("  Email: jane.smith@umd.edu / Password: student123")
        print("  Email: mike.wilson@umd.edu / Password: student123")
        print("\nPending Organizer (cannot login):")
        print("  Email: pending@umd.edu / Password: pending123")
        print("-" * 60)
        
    except Exception as e:
        print(f"\n❌ Error creating sample data: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🔧 Initializing database...")
    init_db()
    print("✅ Database tables created\n")
    
    initialize_all_data()
    
    print("\n🎉 Database initialization complete!")
