from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_, func
from datetime import date, datetime
from app.models.event import Event, EventStatus
import uuid


class EventRepository:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, event_id: str, include_relations: bool = True) -> Optional[Event]:
        query = self.db.query(Event).filter(Event.id == event_id)
        if include_relations:
            query = query.options(
                joinedload(Event.category),
                joinedload(Event.organizer)
            )
        return query.first()
    
    def get_all_published(
        self,
        search: Optional[str] = None,
        category_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        organizer_id: Optional[str] = None,
        availability: Optional[bool] = None,
        sort_by: str = "date",
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[Event], int]:
        query = self.db.query(Event).filter(Event.status == EventStatus.PUBLISHED)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Event.title.ilike(search_pattern),
                    Event.description.ilike(search_pattern),
                    Event.venue.ilike(search_pattern),
                    Event.location.ilike(search_pattern)
                )
            )
        
        if category_id:
            query = query.filter(Event.category_id == category_id)
        
        if start_date:
            query = query.filter(Event.date >= start_date)
        
        if end_date:
            query = query.filter(Event.date <= end_date)
        
        if organizer_id:
            query = query.filter(Event.organizer_id == organizer_id)
        
        if availability:
            query = query.filter(Event.registered_count < Event.capacity)
        
        total_count = query.count()
        
        if sort_by == "title":
            query = query.order_by(Event.title)
        elif sort_by == "popularity":
            query = query.order_by(Event.registered_count.desc())
        else:  
            query = query.order_by(Event.date, Event.start_time)
        
        offset = (page - 1) * limit
        query = query.options(
            joinedload(Event.category),
            joinedload(Event.organizer)
        ).offset(offset).limit(limit)
        
        events = query.all()
        return events, total_count
    
    def get_by_organizer(
        self,
        organizer_id: str,
        status: Optional[EventStatus] = None
    ) -> List[Event]:
        query = self.db.query(Event).filter(Event.organizer_id == organizer_id)
        
        if status:
            query = query.filter(Event.status == status)
        
        return query.options(joinedload(Event.category)).order_by(Event.date.desc()).all()
    
    def create(
        self,
        title: str,
        description: str,
        category_id: str,
        organizer_id: str,
        event_date: date,
        start_time: str,
        end_time: str,
        venue: str,
        location: str,
        capacity: int,
        image_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: EventStatus = EventStatus.PENDING
    ) -> Event:
        from datetime import time
        
        event_id = str(uuid.uuid4())
        
        start_hour, start_minute = map(int, start_time.split(':'))
        end_hour, end_minute = map(int, end_time.split(':'))
        
        event = Event(
            id=event_id,
            title=title,
            description=description,
            category_id=category_id,
            organizer_id=organizer_id,
            date=event_date,
            start_time=time(start_hour, start_minute),
            end_time=time(end_hour, end_minute),
            venue=venue,
            location=location,
            capacity=capacity,
            registered_count=0,
            waitlist_count=0,
            status=status,
            image_url=image_url,
            tags=tags if tags else [],
            is_featured=False
        )
        
        try:
            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)
            return event
        except IntegrityError:
            self.db.rollback()
            raise
    
    def update(self, event: Event, **kwargs) -> Event:
        from datetime import time
        
        for key, value in kwargs.items():
            if hasattr(event, key) and key not in ['id', 'registered_count', 'waitlist_count']:
                # Parse time strings if updating times
                if key in ['start_time', 'end_time'] and isinstance(value, str):
                    hour, minute = map(int, value.split(':'))
                    value = time(hour, minute)
                setattr(event, key, value)
        
        self.db.commit()
        self.db.refresh(event)
        return event
    
    def publish(self, event: Event) -> Event:
        event.status = EventStatus.PUBLISHED
        event.published_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(event)
        return event
    
    def cancel(self, event: Event) -> Event:
        event.status = EventStatus.CANCELLED
        event.cancelled_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(event)
        return event
    
    def increment_registered_count(self, event: Event, count: int = 1) -> Event:
        event.registered_count += count
        self.db.commit()
        self.db.refresh(event)
        return event
    
    def decrement_registered_count(self, event: Event, count: int = 1) -> Event:
        event.registered_count = max(0, event.registered_count - count)
        self.db.commit()
        self.db.refresh(event)
        return event
    
    def increment_waitlist_count(self, event: Event, count: int = 1) -> Event:
        event.waitlist_count += count
        self.db.commit()
        self.db.refresh(event)
        return event
    
    def decrement_waitlist_count(self, event: Event, count: int = 1) -> Event:
        event.waitlist_count = max(0, event.waitlist_count - count)
        self.db.commit()
        self.db.refresh(event)
        return event
    
    def get_pending_events(self) -> List[Event]:
        return self.db.query(Event).filter(
            Event.status == EventStatus.PENDING
        ).options(
            joinedload(Event.category),
            joinedload(Event.organizer)
        ).order_by(Event.created_at).all()
    
    def get_organizer_statistics(self, organizer_id: str) -> dict:
        from sqlalchemy import func
        
        total = self.db.query(func.count(Event.id)).filter(
            Event.organizer_id == organizer_id
        ).scalar()
        
        by_status = self.db.query(
            Event.status, func.count(Event.id)
        ).filter(
            Event.organizer_id == organizer_id
        ).group_by(Event.status).all()
        
        upcoming = self.db.query(func.count(Event.id)).filter(
            Event.organizer_id == organizer_id,
            Event.status == EventStatus.PUBLISHED,
            Event.date >= date.today()
        ).scalar()
        
        total_registrations = self.db.query(func.sum(Event.registered_count)).filter(
            Event.organizer_id == organizer_id
        ).scalar() or 0
        
        return {
            "total": total,
            "upcoming": upcoming,
            "total_registrations": total_registrations,
            "by_status": {status.value: count for status, count in by_status}
        }

    def check_venue_conflict(
        self,
        venue: str,
        event_date: date,
        start_time: str,
        end_time: str,
        exclude_event_id: Optional[str] = None
    ) -> Optional[Event]:
        """
        Check if there's a venue conflict for the given date and time.

        Args:
            venue: Venue name
            event_date: Event date
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            exclude_event_id: Optional event ID to exclude (for updates)

        Returns:
            Optional[Event]: Conflicting event if found, None otherwise
        """
        from datetime import time

        # Parse times
        start = time.fromisoformat(start_time)
        end = time.fromisoformat(end_time)

        # Build query for events at same venue on same date
        query = self.db.query(Event).filter(
            and_(
                Event.venue == venue,
                Event.date == event_date,
                Event.status.in_([EventStatus.PENDING, EventStatus.PUBLISHED])  # Only check non-cancelled events
            )
        )

        # Exclude current event if updating
        if exclude_event_id:
            query = query.filter(Event.id != exclude_event_id)

        # Get all events at this venue on this date
        events = query.all()

        # Check for time overlap
        for existing_event in events:
            existing_start = existing_event.start_time
            existing_end = existing_event.end_time

            # Check if times overlap
            # Overlap occurs if: new_start < existing_end AND new_end > existing_start
            if start < existing_end and end > existing_start:
                return existing_event

        return None

