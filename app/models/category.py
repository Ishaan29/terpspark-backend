from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Category(Base):
    """
    Category model for organizing events.
    Predefined categories: Academic, Career, Cultural, Sports, Arts, 
    Technology, Wellness, Environmental
    """
    __tablename__ = "categories"
    
    
    id = Column(String(36), primary_key=True, index=True)
    
    
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    
    color = Column(String(50), nullable=False, comment="Color code for UI (e.g., 'blue', 'green')")
    icon = Column(String(100), nullable=True, comment="Icon identifier for UI")
    
    
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    
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
    
    
    events = relationship("Event", back_populates="category", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, slug={self.slug})>"
    
    def to_dict(self) -> dict:
        """
        Convert category to dictionary.
        
        Returns:
            dict: Category data as dictionary
        """
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "color": self.color,
            "icon": self.icon,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

