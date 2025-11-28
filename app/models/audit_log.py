"""
Audit Log database model.
Tracks all important actions in the system for security and compliance.
"""
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class AuditAction(str, enum.Enum):
    """Enum for audit log actions."""
    # Authentication
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    
    # Organizer Management
    ORGANIZER_APPROVED = "ORGANIZER_APPROVED"
    ORGANIZER_REJECTED = "ORGANIZER_REJECTED"
    
    # Event Management
    EVENT_CREATED = "EVENT_CREATED"
    EVENT_APPROVED = "EVENT_APPROVED"
    EVENT_REJECTED = "EVENT_REJECTED"
    EVENT_UPDATED = "EVENT_UPDATED"
    EVENT_CANCELLED = "EVENT_CANCELLED"
    EVENT_DUPLICATED = "EVENT_DUPLICATED"
    
    # Category Management
    CATEGORY_CREATED = "CATEGORY_CREATED"
    CATEGORY_UPDATED = "CATEGORY_UPDATED"
    CATEGORY_RETIRED = "CATEGORY_RETIRED"
    
    # Venue Management
    VENUE_CREATED = "VENUE_CREATED"
    VENUE_UPDATED = "VENUE_UPDATED"
    VENUE_RETIRED = "VENUE_RETIRED"
    
    # Registration Management
    REGISTRATION_CREATED = "REGISTRATION_CREATED"
    REGISTRATION_CANCELLED = "REGISTRATION_CANCELLED"
    
    # Waitlist Management
    WAITLIST_JOINED = "WAITLIST_JOINED"
    WAITLIST_LEFT = "WAITLIST_LEFT"
    WAITLIST_PROMOTED = "WAITLIST_PROMOTED"
    
    # Check-in
    ATTENDEE_CHECKED_IN = "ATTENDEE_CHECKED_IN"

    # Communication
    ANNOUNCEMENT_SENT = "ANNOUNCEMENT_SENT"


class TargetType(str, enum.Enum):
    """Enum for target types."""
    USER = "user"
    EVENT = "event"
    CATEGORY = "category"
    VENUE = "venue"
    REGISTRATION = "registration"
    WAITLIST = "waitlist"


class AuditLog(Base):
    """
    Audit Log model for tracking all important system actions.
    This is an append-only table for security and compliance.
    """
    __tablename__ = "audit_logs"
    
    # Primary Key
    id = Column(String(36), primary_key=True, index=True)
    
    # Timestamp
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True
    )
    
    # Action
    action = Column(
        SQLEnum(AuditAction),
        nullable=False,
        index=True
    )
    
    # Actor (who performed the action)
    actor_id = Column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="User who performed the action (null for system actions)"
    )
    actor_name = Column(String(255), nullable=True)
    actor_role = Column(String(50), nullable=True)
    
    # Target (what was acted upon)
    target_type = Column(SQLEnum(TargetType), nullable=True)
    target_id = Column(String(36), nullable=True, index=True)
    target_name = Column(String(500), nullable=True)
    
    # Details
    details = Column(
        Text,
        nullable=True,
        comment="Human-readable description of the action"
    )
    
    # Additional metadata stored as JSON
    extra_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional context and data related to the action"
    )
    
    # Request Information
    ip_address = Column(String(45), nullable=True, comment="IPv4 or IPv6 address")
    user_agent = Column(String(500), nullable=True, comment="Browser/client user agent")
    
    # Relationships
    actor = relationship("User", foreign_keys=[actor_id], backref="audit_logs")
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, actor_id={self.actor_id})>"
    
    def to_dict(self) -> dict:
        """
        Convert audit log to dictionary.
        
        Returns:
            dict: Audit log data as dictionary
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "action": self.action.value,
            "actor": {
                "id": self.actor_id,
                "name": self.actor_name,
                "role": self.actor_role
            } if self.actor_id else None,
            "target": {
                "type": self.target_type.value if self.target_type else None,
                "id": self.target_id,
                "name": self.target_name
            } if self.target_id else None,
            "details": self.details,
            "metadata": self.extra_metadata if self.extra_metadata else {},
            "ipAddress": self.ip_address,
            "userAgent": self.user_agent,
        }

