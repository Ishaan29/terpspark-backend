from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import date
from app.models.event import Event, EventStatus
from app.models.category import Category
from app.models.venue import Venue
from app.repositories.event_repository import EventRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.venue_repository import VenueRepository
from app.repositories.registration_repository import RegistrationRepository


class EventService:
    
    def __init__(self, db: Session):
        self.db = db
        self.event_repo = EventRepository(db)
        self.category_repo = CategoryRepository(db)
        self.venue_repo = VenueRepository(db)
        self.registration_repo = RegistrationRepository(db)
    
    def get_published_events(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        organizer: Optional[str] = None,
        availability: Optional[bool] = None,
        sort_by: str = "date",
        page: int = 1,
        limit: int = 20,
        user_id: Optional[str] = None,
        exclude_registered: bool = False
    ) -> Tuple[List[Event], int]:
        # Validate page and limit
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page number must be at least 1"
            )
        
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100"
            )
        
        category_id = None
        if category:
            cat = self.category_repo.get_by_slug(category)
            if not cat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Category '{category}' not found"
                )
            category_id = cat.id
        
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            try:
                start_date_obj = date.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_date must be in YYYY-MM-DD format"
                )
        
        if end_date:
            try:
                end_date_obj = date.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="end_date must be in YYYY-MM-DD format"
                )
        
        valid_sort_options = ["date", "title", "popularity"]
        if sort_by not in valid_sort_options:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"sort_by must be one of: {', '.join(valid_sort_options)}"
            )
        
        try:
            events, total_count = self.event_repo.get_all_published(
                search=search,
                category_id=category_id,
                start_date=start_date_obj,
                end_date=end_date_obj,
                organizer_id=None,
                availability=availability,
                sort_by=sort_by,
                page=page,
                limit=limit
            )

            
            if user_id and exclude_registered:
                
                user_registrations = self.registration_repo.get_user_registrations(
                    user_id=user_id,
                    status=None, 
                    include_past=False
                )
                registered_event_ids = {reg.event_id for reg in user_registrations}

                filtered_events = [event for event in events if event.id not in registered_event_ids]

                return filtered_events, total_count

            return events, total_count
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve events: {str(e)}"
            )
    
    def get_event_by_id(self, event_id: str) -> Event:
        event = self.event_repo.get_by_id(event_id, include_relations=True)
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        if event.status != EventStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        return event
    
    def get_event_by_id_for_user(
        self,
        event_id: str,
        user_id: Optional[str] = None,
        is_admin: bool = False
    ) -> Event:
        event = self.event_repo.get_by_id(event_id, include_relations=True)
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        if event.status == EventStatus.PUBLISHED:
            return event
        elif is_admin or (user_id and event.organizer_id == user_id):
            return event
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
    
    def get_all_categories(self, active_only: bool = True) -> List[Category]:
        try:
            return self.category_repo.get_all(active_only=active_only)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve categories: {str(e)}"
            )
    
    def get_all_venues(self, active_only: bool = True) -> List[Venue]:
        try:
            return self.venue_repo.get_all(active_only=active_only)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve venues: {str(e)}"
            )

