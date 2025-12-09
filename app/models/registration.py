from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class CheckInStatus(str, enum.Enum):
    NOT_CHECKED_IN = "not_checked_in"
    CHECKED_IN = "checked_in"


class RegistrationStatus(str, enum.Enum):    
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Registration(Base):
    __tablename__ = "registrations"
    
    
    id = Column(String(36), primary_key=True, index=True)
    
    
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=False, index=True)
    
    
    status = Column(
        SQLEnum(RegistrationStatus),
        nullable=False,
        default=RegistrationStatus.CONFIRMED,
        index=True
    )
    
    
    ticket_code = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Format: TKT-{timestamp}-{eventId}"
    )
    qr_code = Column(Text, nullable=True, comment="Base64 encoded QR code or URL")
    
    
    check_in_status = Column(
        SQLEnum(CheckInStatus),
        nullable=False,
        default=CheckInStatus.NOT_CHECKED_IN
    )
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    
    
    guests = Column(
        JSON,
        nullable=True,
        comment="Array of guest objects with name and email"
    )
    
    
    sessions = Column(JSON, nullable=True, comment="Array of session IDs")
    
    
    reminder_sent = Column(Boolean, nullable=False, default=False)
    
    
    registered_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", backref="registrations")
    event = relationship("Event", back_populates="registrations")
    
    def __repr__(self) -> str:
        return f"<Registration(id={self.id}, user_id={self.user_id}, event_id={self.event_id}, status={self.status})>"
    
    @property
    def guest_count(self) -> int:
        """Get number of guests."""
        if not self.guests:
            return 0
        return len(self.guests)
    
    @property
    def total_attendees(self) -> int:
        """Get total number of attendees (user + guests)."""
        return 1 + self.guest_count
    
    def to_dict(self, include_event: bool = False, include_user: bool = False) -> dict:
        """
        Convert registration to dictionary.
        
        Args:
            include_event: Whether to include event details
            include_user: Whether to include user details
            
        Returns:
            dict: Registration data as dictionary
        """
        reg_dict = {
            "id": self.id,
            "userId": self.user_id,
            "eventId": self.event_id,
            "status": self.status.value,
            "ticketCode": self.ticket_code,
            "qrCode": self.qr_code,
            "registeredAt": self.registered_at.isoformat() if self.registered_at else None,
            "checkInStatus": self.check_in_status.value,
            "checkedInAt": self.checked_in_at.isoformat() if self.checked_in_at else None,
            "guests": self.guests if self.guests else [],
            "sessions": self.sessions if self.sessions else [],
            "reminderSent": self.reminder_sent,
            "cancelledAt": self.cancelled_at.isoformat() if self.cancelled_at else None,
        }
        
        if include_event and self.event:
            reg_dict["event"] = {
                "id": self.event.id,
                "title": self.event.title,
                "date": self.event.date.isoformat() if self.event.date else None,
                "startTime": self.event.start_time.strftime("%H:%M") if self.event.start_time else None,
                "venue": self.event.venue,
                "organizer": {
                    "name": self.event.organizer.name
                } if self.event.organizer else None
            }
        
        if include_user and self.user:
            reg_dict["user"] = {
                "id": self.user.id,
                "name": self.user.name,
                "email": self.user.email
            }
        
        return reg_dict

