from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.venue import Venue
import uuid


class VenueRepository:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, venue_id: str) -> Optional[Venue]:
        return self.db.query(Venue).filter(Venue.id == venue_id).first()
    
    def get_all(self, active_only: bool = True) -> List[Venue]:
        query = self.db.query(Venue)
        if active_only:
            query = query.filter(Venue.is_active == True)
        return query.order_by(Venue.name).all()
    
    def create(
        self,
        name: str,
        building: str,
        capacity: Optional[int] = None,
        facilities: Optional[List[str]] = None
    ) -> Venue:
        venue_id = str(uuid.uuid4())
        
        venue = Venue(
            id=venue_id,
            name=name,
            building=building,
            capacity=capacity,
            facilities=facilities if facilities else [],
            is_active=True
        )
        
        try:
            self.db.add(venue)
            self.db.commit()
            self.db.refresh(venue)
            return venue
        except IntegrityError:
            self.db.rollback()
            raise
    
    def update(self, venue: Venue, **kwargs) -> Venue:
        for key, value in kwargs.items():
            if hasattr(venue, key) and key != 'id':
                setattr(venue, key, value)
        
        self.db.commit()
        self.db.refresh(venue)
        return venue
    
    def toggle_active(self, venue: Venue) -> Venue:
        venue.is_active = not venue.is_active
        self.db.commit()
        self.db.refresh(venue)
        return venue

