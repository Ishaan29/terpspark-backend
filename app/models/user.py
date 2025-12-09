from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    """Enum for user roles."""
    STUDENT = "student"
    ORGANIZER = "organizer"
    ADMIN = "admin"


class User(Base):
    """
    User model representing all users in the system.
    Supports three roles: student, organizer, and admin.
    """
    __tablename__ = "users"
    
    # Primary Key
    id = Column(String(36), primary_key=True, index=True)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # Hashed password
    
    # Profile Information
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    department = Column(String(100), nullable=True)
    
    # Role & Permissions
    role = Column(
        SQLEnum(UserRole),
        nullable=False,
        default=UserRole.STUDENT,
        index=True
    )
    is_approved = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="For organizers - must be approved by admin"
    )
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Profile Extensions (Phase 6)
    profile_picture = Column(String(500), nullable=True)
    graduation_year = Column(String(4), nullable=True)
    bio = Column(String(1000), nullable=True)
    # interests stored as JSON in future, for now we'll keep it simple
    
    # Timestamps
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
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    def to_dict(self, include_password: bool = False) -> dict:
        """
        Convert user to dictionary.
        
        Args:
            include_password: Whether to include hashed password (default: False)
            
        Returns:
            dict: User data as dictionary
        """
        user_dict = {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role.value,
            "isApproved": self.is_approved,
            "isActive": self.is_active,
            "phone": self.phone,
            "department": self.department,
            "profilePicture": self.profile_picture,
            "graduationYear": self.graduation_year,
            "bio": self.bio,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
            "lastLogin": self.last_login.isoformat() if self.last_login else None,
        }
        
        if include_password:
            user_dict["password"] = self.password
            
        return user_dict
    
    @property
    def is_student(self) -> bool:
        """Check if user is a student."""
        return self.role == UserRole.STUDENT
    
    @property
    def is_organizer(self) -> bool:
        """Check if user is an organizer."""
        return self.role == UserRole.ORGANIZER
    
    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN
    
    @property
    def can_login(self) -> bool:
        """Check if user can login (active and approved if organizer)."""
        if not self.is_active:
            return False
        if self.is_organizer and not self.is_approved:
            return False
        return True
