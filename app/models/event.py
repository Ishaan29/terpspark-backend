from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Enum as SQLEnum, JSON, ForeignKey, Date, Time
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class EventStatus(str, enum.Enum):
    """Enum for event status."""
    DRAFT = "draft"
    PENDING = "pending"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


class Event(Base):
    """
    Event model representing events in the system.
    Events can be in different statuses: draft, pending, published, cancelled.
    """
    __tablename__ = "events"
    
    
    id = Column(String(36), primary_key=True, index=True)
    
    
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False, index=True)
    organizer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    
    date = Column(Date, nullable=False, index=True, comment="Event date in YYYY-MM-DD")
    start_time = Column(Time, nullable=False, comment="Event start time in HH:MM (24-hour)")
    end_time = Column(Time, nullable=False, comment="Event end time in HH:MM (24-hour)")
    
    
    venue = Column(String(200), nullable=False)
    location = Column(String(500), nullable=False, comment="Detailed location description")
    
    
    capacity = Column(Integer, nullable=False, comment="Maximum number of attendees (1-5000)")
    registered_count = Column(Integer, nullable=False, default=0, comment="Current number of registered attendees")
    waitlist_count = Column(Integer, nullable=False, default=0, comment="Current number on waitlist")
    
    
    status = Column(
        SQLEnum(EventStatus),
        nullable=False,
        default=EventStatus.PENDING,
        index=True
    )
    
    
    image_url = Column(String(500), nullable=True, comment="URL to event image")
    
    
    tags = Column(JSON, nullable=True, comment="Array of tag strings")
    
    
    is_featured = Column(Boolean, nullable=False, default=False, comment="Whether event is featured")
    
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    published_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)


    category = relationship("Category", back_populates="events")
    organizer = relationship("User", foreign_keys=[organizer_id], backref="organized_events")
    registrations = relationship("Registration", back_populates="event", lazy="dynamic")
    waitlist = relationship("WaitlistEntry", back_populates="event", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<Event(id={self.id}, title={self.title}, status={self.status})>"
    
    @property
    def remaining_capacity(self) -> int:
        """Calculate remaining capacity."""
        return max(0, self.capacity - self.registered_count)
    
    @property
    def is_full(self) -> bool:
        """Check if event is at capacity."""
        return self.registered_count >= self.capacity
    
    def to_dict(self, include_organizer: bool = True, include_category: bool = True) -> dict:
        """
        Convert event to dictionary.
        
        Args:
            include_organizer: Whether to include organizer details
            include_category: Whether to include category details
            
        Returns:
            dict: Event data as dictionary
        """
        event_dict = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "categoryId": self.category_id,
            "organizerId": self.organizer_id,
            "date": self.date.isoformat() if self.date else None,
            "startTime": self.start_time.strftime("%H:%M") if self.start_time else None,
            "endTime": self.end_time.strftime("%H:%M") if self.end_time else None,
            "venue": self.venue,
            "location": self.location,
            "capacity": self.capacity,
            "registeredCount": self.registered_count,
            "waitlistCount": self.waitlist_count,
            "remainingCapacity": self.remaining_capacity,
            "status": self.status.value,
            "imageUrl": self.image_url,
            "tags": self.tags if self.tags else [],
            "isFeatured": self.is_featured,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
            "publishedAt": self.published_at.isoformat() if self.published_at else None,
            "cancelledAt": self.cancelled_at.isoformat() if self.cancelled_at else None,
        }
        
        if include_category and self.category:
            event_dict["category"] = {
                "id": self.category.id,
                "name": self.category.name,
                "slug": self.category.slug,
                "color": self.category.color
            }
        
        if include_organizer and self.organizer:
            event_dict["organizer"] = {
                "id": self.organizer.id,
                "name": self.organizer.name,
                "email": self.organizer.email,
                "department": self.organizer.department
            }
        
        return event_dict

