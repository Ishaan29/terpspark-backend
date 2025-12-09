from sqlalchemy import Column, String, Boolean, DateTime, Integer, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class Venue(Base):
    __tablename__ = "venues"
    
    id = Column(String(36), primary_key=True, index=True)
    
    name = Column(String(200), nullable=False)
    building = Column(String(200), nullable=False)
    capacity = Column(Integer, nullable=True, comment="Maximum capacity of venue")
    
    facilities = Column(
        JSON,
        nullable=True,
        comment="Array of available facilities (e.g., ['Projector', 'WiFi', 'Microphone'])"
    )
    
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
    
    def __repr__(self) -> str:
        return f"<Venue(id={self.id}, name={self.name}, building={self.building})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "building": self.building,
            "capacity": self.capacity,
            "facilities": self.facilities if self.facilities else [],
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

