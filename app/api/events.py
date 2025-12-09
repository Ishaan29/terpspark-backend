from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.event_service import EventService
from app.schemas.event import (
    EventsListResponse,
    EventDetailResponse,
    EventListResponse,
    PaginationInfo,
    CategoryInfo,
    OrganizerInfo
)
from app.schemas.category import CategoriesResponse, CategoryResponse
from app.schemas.venue import VenuesResponse, VenueResponse
from app.schemas.auth import ErrorResponse
from app.middleware.auth import get_current_active_user
from app.models.user import User, UserRole
from app.services.registration_service import RegistrationService


router = APIRouter(prefix="/api", tags=["Events"])


@router.get(
    "/events",
    response_model=EventsListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        404: {"model": ErrorResponse, "description": "Category not found"}
    }
)
async def get_events(
    search: Optional[str] = Query(
        None,
        description="Search in title, description, tags, venue, organizer"
    ),
    category: Optional[str] = Query(
        None,
        description="Category slug (academic, career, cultural, etc.)"
    ),
    startDate: Optional[str] = Query(
        None,
        alias="startDate",
        description="ISO 8601 date (filter events after this date)"
    ),
    endDate: Optional[str] = Query(
        None,
        alias="endDate",
        description="ISO 8601 date (filter events before this date)"
    ),
    organizer: Optional[str] = Query(
        None,
        description="Organizer name search"
    ),
    availability: Optional[bool] = Query(
        None,
        description="If true, only show events with available spots"
    ),
    sortBy: Optional[str] = Query(
        "date",
        alias="sortBy",
        description="Sort by: 'date', 'title', or 'popularity' (default: 'date')"
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number (default: 1)"
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Items per page (default: 20, max: 100)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve paginated list of published events with optional filters.
    
    **Business Rules:**
    - Only returns events with status "published"
    - Doesn't return past events unless specifically requested
    - Calculates registeredCount from active (confirmed) registrations
    - Includes guests in registeredCount
    - Sorts by date ascending by default (soonest events first)
    
    **Query Parameters:**
    - **search**: Search term for title, description, tags, venue, organizer
    - **category**: Category slug to filter by
    - **startDate**: Filter events on or after this date (YYYY-MM-DD)
    - **endDate**: Filter events on or before this date (YYYY-MM-DD)
    - **organizer**: Filter by organizer name
    - **availability**: Only show events with available spots
    - **sortBy**: Sort by 'date', 'title', or 'popularity'
    - **page**: Page number (starts at 1)
    - **limit**: Items per page (1-100)
    
    **Returns:**
    - List of events with pagination information
    """
    event_service = EventService(db)
    
    try:
        events, total_count = event_service.get_published_events(
            search=search,
            category=category,
            start_date=startDate,
            end_date=endDate,
            organizer=organizer,
            availability=availability,
            sort_by=sortBy,
            page=page,
            limit=limit
        )
        ## make a call to the registrations API to get the registrations for the user
       

        ## if the user is a student, we need to check if they are registered for the event
        if current_user and current_user.role == UserRole.STUDENT:
            registration_service = RegistrationService(db)
            registrations = registration_service.get_user_registrations(user_id=current_user.id)
            events = [event for event in events if event.id not in [registration.event_id for registration in registrations]]

        ## if the user is an organizer, only show the events that they are organizing
        # if current_user and current_user.role == UserRole.ORGANIZER:
        #     events = [event for event in events if event.organizer_id == current_user.id]
                
        
        # Convert events to response format
        event_responses = []
        for event in events:
            event_data = EventListResponse(
                id=event.id,
                title=event.title,
                description=event.description,
                category=CategoryInfo(
                    id=event.category.id,
                    name=event.category.name,
                    slug=event.category.slug,
                    color=event.category.color
                ) if event.category else None,
                organizer=OrganizerInfo(
                    id=event.organizer.id,
                    name=event.organizer.name,
                    email=event.organizer.email,
                    department=event.organizer.department
                ) if event.organizer else None,
                date=event.date.isoformat() if event.date else None,
                startTime=event.start_time.strftime("%H:%M") if event.start_time else None,
                endTime=event.end_time.strftime("%H:%M") if event.end_time else None,
                venue=event.venue,
                location=event.location,
                capacity=event.capacity,
                registeredCount=event.registered_count,
                waitlistCount=event.waitlist_count,
                status=event.status.value,
                imageUrl=event.image_url,
                tags=event.tags if event.tags else [],
                isFeatured=event.is_featured,
                createdAt=event.created_at.isoformat() if event.created_at else None,
                publishedAt=event.published_at.isoformat() if event.published_at else None
            )
            event_responses.append(event_data)
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        
        pagination = PaginationInfo(
            currentPage=page,
            totalPages=total_pages,
            totalItems=total_count,
            itemsPerPage=limit
        )
        
        return EventsListResponse(
            success=True,
            events=event_responses,
            pagination=pagination
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve events: {str(e)}"
        )


@router.get(
    "/events/{event_id}",
    response_model=EventDetailResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Event not found"}
    }
)
async def get_event_detail(
    event_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific event.
    
    **Business Rules:**
    - Calculates remainingCapacity = capacity - registeredCount
    - Only returns if event is published (or user is organizer/admin)
    
    **Path Parameters:**
    - **event_id**: Unique event identifier
    
    **Returns:**
    - Detailed event information including:
      - Full description
      - Category details
      - Organizer information
      - Date, time, and location
      - Capacity and registration counts
      - Remaining capacity
      - Tags and featured status
    """
    event_service = EventService(db)
    
    try:
        event = event_service.get_event_by_id(event_id)
        
        # Build response with full event details
        event_response = EventDetailResponse(
            success=True,
            event={
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "categoryId": event.category_id,
                "organizerId": event.organizer_id,
                "date": event.date.isoformat() if event.date else None,
                "startTime": event.start_time.strftime("%H:%M") if event.start_time else None,
                "endTime": event.end_time.strftime("%H:%M") if event.end_time else None,
                "venue": event.venue,
                "location": event.location,
                "capacity": event.capacity,
                "registeredCount": event.registered_count,
                "waitlistCount": event.waitlist_count,
                "remainingCapacity": event.remaining_capacity,
                "status": event.status.value,
                "imageUrl": event.image_url,
                "tags": event.tags if event.tags else [],
                "isFeatured": event.is_featured,
                "createdAt": event.created_at.isoformat() if event.created_at else None,
                "updatedAt": event.updated_at.isoformat() if event.updated_at else None,
                "publishedAt": event.published_at.isoformat() if event.published_at else None,
                "cancelledAt": event.cancelled_at.isoformat() if event.cancelled_at else None,
                "category": {
                    "id": event.category.id,
                    "name": event.category.name,
                    "slug": event.category.slug,
                    "color": event.category.color
                } if event.category else None,
                "organizer": {
                    "id": event.organizer.id,
                    "name": event.organizer.name,
                    "email": event.organizer.email,
                    "department": event.organizer.department
                } if event.organizer else None
            }
        )
        
        return event_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve event: {str(e)}"
        )


@router.get(
    "/categories",
    response_model=CategoriesResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_categories(
    db: Session = Depends(get_db)
):
    """
    Get list of all active event categories.
    
    **Predefined Categories:**
    1. Academic (blue) - Academic events, workshops, lectures
    2. Career (green) - Career fairs, networking, job opportunities
    3. Cultural (purple) - Cultural celebrations, multicultural events
    4. Sports (red) - Sports events, tournaments, fitness
    5. Arts (pink) - Art exhibitions, performances, creative workshops
    6. Technology (indigo) - Tech talks, hackathons, innovation
    7. Wellness (teal) - Health, wellness, mindfulness
    8. Environmental (emerald) - Environmental awareness, sustainability
    
    **Returns:**
    - List of active categories with:
      - ID, name, slug
      - Description
      - Color code for UI
      - Icon identifier
    """
    event_service = EventService(db)
    
    try:
        categories = event_service.get_all_categories(active_only=True)
        
        category_responses = [
            CategoryResponse(
                id=cat.id,
                name=cat.name,
                slug=cat.slug,
                description=cat.description,
                color=cat.color,
                icon=cat.icon,
                isActive=cat.is_active,
                createdAt=cat.created_at.isoformat() if cat.created_at else None,
                updatedAt=cat.updated_at.isoformat() if cat.updated_at else None
            )
            for cat in categories
        ]
        
        return CategoriesResponse(
            success=True,
            categories=category_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve categories: {str(e)}"
        )


@router.get(
    "/venues",
    response_model=VenuesResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_venues(
    db: Session = Depends(get_db)
):
    """
    Get list of all active venues.
    
    **Returns:**
    - List of active venues with:
      - ID, name, building
      - Capacity
      - Available facilities (projector, WiFi, etc.)
    """
    event_service = EventService(db)
    
    try:
        venues = event_service.get_all_venues(active_only=True)
        
        venue_responses = [
            VenueResponse(
                id=venue.id,
                name=venue.name,
                building=venue.building,
                capacity=venue.capacity,
                facilities=venue.facilities if venue.facilities else [],
                isActive=venue.is_active,
                createdAt=venue.created_at.isoformat() if venue.created_at else None,
                updatedAt=venue.updated_at.isoformat() if venue.updated_at else None
            )
            for venue in venues
        ]
        
        return VenuesResponse(
            success=True,
            venues=venue_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve venues: {str(e)}"
        )


# Health check endpoint
@router.get("/events/health")
async def health_check():
    """
    Health check endpoint for events API.
    
    **Returns:**
    - API status and version
    """
    return {
        "status": "healthy",
        "service": "TerpSpark Events API",
        "version": "1.0.0",
        "phase": "Phase 2: Event Discovery & Browse"
    }

