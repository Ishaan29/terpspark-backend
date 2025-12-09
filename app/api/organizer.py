"""
Organizer API routes for Phase 4: Organizer Management.
Handles event creation, management, attendee management, and communication.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import io

from app.core.database import get_db
from app.services.organizer_service import OrganizerService
from app.middleware.auth import require_organizer, get_current_user
from app.models.user import User
from app.models.event import EventStatus
from app.schemas.event import (
    EventCreate,
    EventUpdate,
    EventResponse,
    OrganizerEventsResponse,
    EventStatistics,
    CategoryInfo,
    OrganizerInfo
)
from app.schemas.registration import (
    AttendeesResponse,
    AttendeeInfo,
    AttendeeStatistics
)
from app.schemas.waitlist import WaitlistResponse
from app.schemas.auth import ErrorResponse, MessageResponse
from pydantic import BaseModel, Field


# Additional schemas for organizer endpoints
class EventCreateResponse(BaseModel):
    """Schema for event creation response."""
    success: bool = True
    message: str = "Event created successfully"
    event: EventResponse


class EventUpdateResponse(BaseModel):
    """Schema for event update response."""
    success: bool = True
    message: str = "Event updated successfully"
    event: EventResponse


class EventCancelResponse(BaseModel):
    """Schema for event cancellation response."""
    success: bool = True
    message: str = "Event cancelled successfully"


class EventDuplicateResponse(BaseModel):
    """Schema for event duplication response."""
    success: bool = True
    message: str = "Event duplicated successfully"
    event: EventResponse


class OrganizerStatisticsResponse(BaseModel):
    """Schema for organizer statistics response."""
    success: bool = True
    statistics: dict


class CheckInResponse(BaseModel):
    """Schema for check-in response."""
    success: bool = True
    message: str = "Attendee checked in successfully"
    registration: dict


class AnnouncementCreate(BaseModel):
    """Schema for creating an announcement."""
    subject: str = Field(..., min_length=5, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)


class AnnouncementResponse(BaseModel):
    """Schema for announcement response."""
    success: bool = True
    message: str
    recipientCount: int


class WaitlistEntryInfo(BaseModel):
    """Schema for waitlist entry in organizer view."""
    id: str
    userId: str
    position: int
    name: str
    email: str
    joinedAt: str
    notificationPreference: str


class EventWaitlistResponse(BaseModel):
    """Schema for event waitlist response."""
    success: bool = True
    waitlist: List[WaitlistEntryInfo]
    totalCount: int


# Create router
router = APIRouter(prefix="/api/organizer", tags=["Organizer"])


def get_client_info(request: Request) -> tuple:
    """Extract client IP and user agent from request."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


def event_to_response(event) -> EventResponse:
    """Convert Event model to EventResponse."""
    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        categoryId=event.category_id,
        organizerId=event.organizer_id,
        date=event.date.isoformat() if event.date else None,
        startTime=event.start_time.strftime("%H:%M") if event.start_time else None,
        endTime=event.end_time.strftime("%H:%M") if event.end_time else None,
        venue=event.venue,
        location=event.location,
        capacity=event.capacity,
        registeredCount=event.registered_count,
        waitlistCount=event.waitlist_count,
        remainingCapacity=event.remaining_capacity,
        status=event.status.value,
        imageUrl=event.image_url,
        tags=event.tags if event.tags else [],
        isFeatured=event.is_featured,
        createdAt=event.created_at.isoformat() if event.created_at else None,
        updatedAt=event.updated_at.isoformat() if event.updated_at else None,
        publishedAt=event.published_at.isoformat() if event.published_at else None,
        cancelledAt=event.cancelled_at.isoformat() if event.cancelled_at else None,
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
        ) if event.organizer else None
    )


# ============================================
# Event Management (6 APIs)
# ============================================

@router.post(
    "/events",
    response_model=EventCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Not an approved organizer"},
        404: {"model": ErrorResponse, "description": "Category not found"},
        409: {"model": ErrorResponse, "description": "Venue conflict - already booked"}
    }
)
async def create_event(
    event_data: EventCreate,
    request: Request,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db)
):
    """
    Create a new event.

    **Business Rules:**
    - Only approved organizers can create events
    - Events start with 'pending' status (require admin approval)
    - Category must exist and be active
    - Event date must be in the future
    - End time must be after start time
    - Venue must not have conflicts (checked against date and time)

    **Venue Conflict Checking:**
    - System checks if the venue is already booked for the same date/time
    - Conflicts are checked against pending and published events only
    - Returns 409 Conflict error if venue is already booked

    **Required Fields:**
    - title (5-200 characters)
    - description (min 50 characters)
    - categoryId
    - date (YYYY-MM-DD, must be in future)
    - startTime (HH:MM)
    - endTime (HH:MM, after startTime)
    - venue (2-200 characters)
    - location (5-500 characters)
    - capacity (1-5000)

    **Optional Fields:**
    - imageUrl
    - tags (array of strings)

    **Returns:**
    - Created event details
    """
    ip_address, user_agent = get_client_info(request)
    
    organizer_service = OrganizerService(db)
    
    try:
        event = organizer_service.create_event(
            event_data=event_data,
            organizer=current_user,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return EventCreateResponse(
            success=True,
            message="Event created successfully. It will be visible after admin approval.",
            event=event_to_response(event)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )


@router.get(
    "/events",
    response_model=OrganizerEventsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Not an approved organizer"}
    }
)
async def get_organizer_events(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: draft, pending, published, cancelled"
    ),
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db)
):
    """
    Get all events created by the current organizer.
    
    **Business Rules:**
    - Returns all events regardless of status
    - Includes statistics about events
    
    **Query Parameters:**
    - status: Filter by event status (draft, pending, published, cancelled)
    
    **Returns:**
    - List of events with details
    - Statistics (total, by status)
    """
    organizer_service = OrganizerService(db)
    
    try:
        # Parse status filter
        event_status = None
        if status_filter:
            try:
                event_status = EventStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: draft, pending, published, cancelled"
                )
        
        events, stats = organizer_service.get_organizer_events(
            organizer=current_user,
            status_filter=event_status
        )
        
        # Convert events to response format
        event_responses = [event_to_response(event) for event in events]
        
        # Build statistics
        statistics = EventStatistics(
            total=stats.get("total", 0),
            draft=stats.get("by_status", {}).get("draft", 0),
            pending=stats.get("by_status", {}).get("pending", 0),
            published=stats.get("by_status", {}).get("published", 0),
            cancelled=stats.get("by_status", {}).get("cancelled", 0)
        )
        
        return OrganizerEventsResponse(
            success=True,
            events=event_responses,
            statistics=statistics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve events: {str(e)}"
        )


@router.put(
    "/events/{event_id}",
    response_model=EventUpdateResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Event not found"},
        409: {"model": ErrorResponse, "description": "Venue conflict - already booked"}
    }
)
async def update_event(
    event_id: str,
    event_data: EventUpdate,
    request: Request,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db)
):
    """
    Update an existing event with complete event data.

    **Business Rules:**
    - Only event owner or admin can update
    - Cannot update cancelled events
    - Cannot reduce capacity below current registration count
    - All fields are required (same as create event)
    - All validations from event creation apply
    - Status can be updated (see status rules below)
    - Venue conflicts are checked (excluding current event)

    **Venue Conflict Checking:**
    - System checks if the venue is already booked for the same date/time
    - Current event is excluded from conflict check
    - Conflicts are checked against pending and published events only
    - Returns 409 Conflict error if venue is already booked

    **Path Parameters:**
    - event_id: Event ID to update

    **Required Fields:**
    - title (5-200 characters)
    - description (min 50 characters)
    - categoryId
    - date (YYYY-MM-DD, must be in future)
    - startTime (HH:MM, 24-hour format)
    - endTime (HH:MM, must be after startTime)
    - venue (2-200 characters)
    - location (5-500 characters)
    - capacity (1-5000, cannot be less than registered count)

    **Optional Fields:**
    - imageUrl (max 500 characters)
    - tags (array of strings)
    - status (draft, pending, published, cancelled)

    **Status Update Rules:**
    - Organizers can set status to: 'draft' or 'pending'
    - Only admins can set status to: 'published'
    - To cancel, use the cancel endpoint (not via status update)
    - If status is not provided, it remains unchanged

    **Returns:**
    - Updated event details
    """
    ip_address, user_agent = get_client_info(request)
    
    organizer_service = OrganizerService(db)
    
    try:
        event = organizer_service.update_event(
            event_id=event_id,
            event_data=event_data,
            organizer=current_user,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return EventUpdateResponse(
            success=True,
            message="Event updated successfully",
            event=event_to_response(event)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event: {str(e)}"
        )


@router.post(
    "/events/{event_id}/cancel",
    response_model=EventCancelResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Event already cancelled"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Event not found"}
    }
)
async def cancel_event(
    event_id: str,
    request: Request,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db)
):
    """
    Cancel an event.
    
    **Business Rules:**
    - Only event owner or admin can cancel
    - Cannot cancel already cancelled events
    - Registered attendees will be notified (planned)
    - Waitlist entries remain for reference
    
    **Path Parameters:**
    - event_id: Event ID to cancel
    
    **Returns:**
    - Success message
    """
    ip_address, user_agent = get_client_info(request)
    
    organizer_service = OrganizerService(db)
    
    try:
        organizer_service.cancel_event(
            event_id=event_id,
            organizer=current_user,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return EventCancelResponse(
            success=True,
            message="Event cancelled successfully. Registered attendees will be notified."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel event: {str(e)}"
        )


@router.post(
    "/events/{event_id}/duplicate",
    response_model=EventDuplicateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Event not found"}
    }
)
async def duplicate_event(
    event_id: str,
    request: Request,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db)
):
    """
    Duplicate an existing event.
    
    **Business Rules:**
    - Only event owner or admin can duplicate
    - New event gets " (Copy)" appended to title
    - New event starts in 'draft' status
    - Registrations and waitlist are NOT copied
    - All other details are copied
    
    **Path Parameters:**
    - event_id: Event ID to duplicate
    
    **Returns:**
    - New duplicated event details
    """
    ip_address, user_agent = get_client_info(request)
    
    organizer_service = OrganizerService(db)
    
    try:
        event = organizer_service.duplicate_event(
            event_id=event_id,
            organizer=current_user,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return EventDuplicateResponse(
            success=True,
            message="Event duplicated successfully. Update the date and submit for approval.",
            event=event_to_response(event)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate event: {str(e)}"
        )


@router.get(
    "/statistics",
    response_model=OrganizerStatisticsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Not an approved organizer"}
    }
)
async def get_organizer_statistics(
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db)
):
    """
    Get statistics for the current organizer.
    
    **Returns:**
    - totalEvents: Total number of events created
    - upcomingEvents: Number of upcoming published events
    - totalRegistrations: Total registrations across all events
    - eventsByStatus: Breakdown by status (draft, pending, published, cancelled)
    """
    organizer_service = OrganizerService(db)
    
    try:
        statistics = organizer_service.get_organizer_statistics(current_user)
        
        return OrganizerStatisticsResponse(
            success=True,
            statistics=statistics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


# ============================================
# Attendee Management (3 APIs)
# ============================================

@router.get(
    "/events/{event_id}/attendees",
    response_model=AttendeesResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Event not found"}
    }
)
async def get_event_attendees(
    event_id: str,
    checkInStatus: Optional[str] = Query(
        None,
        alias="checkInStatus",
        description="Filter by check-in status: checked_in, not_checked_in"
    ),
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db)
):
    """
    Get list of attendees for an event.
    
    **Business Rules:**
    - Only event owner or admin can view attendees
    - Only shows confirmed registrations
    - Includes guest information
    
    **Path Parameters:**
    - event_id: Event ID
    
    **Query Parameters:**
    - checkInStatus: Filter by check-in status (checked_in, not_checked_in)
    
    **Returns:**
    - List of attendees with details
    - Statistics (total, checked-in, capacity usage)
    """
    organizer_service = OrganizerService(db)
    
    try:
        attendees, statistics = organizer_service.get_event_attendees(
            event_id=event_id,
            organizer=current_user,
            check_in_filter=checkInStatus
        )
        
        # Convert to response format
        attendee_responses = [
            AttendeeInfo(
                id=a["id"] or "",
                registrationId=a["registrationId"],
                name=a["name"],
                email=a["email"],
                registeredAt=a["registeredAt"] or "",
                checkInStatus=a["checkInStatus"],
                checkedInAt=a["checkedInAt"],
                guests=a["guests"]
            )
            for a in attendees
        ]
        
        stats_response = AttendeeStatistics(
            totalRegistrations=statistics["totalRegistrations"],
            checkedIn=statistics["checkedIn"],
            notCheckedIn=statistics["notCheckedIn"],
            totalAttendees=statistics["totalAttendees"],
            capacityUsed=statistics["capacityUsed"]
        )
        
        return AttendeesResponse(
            success=True,
            attendees=attendee_responses,
            statistics=stats_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve attendees: {str(e)}"
        )


@router.get(
    "/events/{event_id}/attendees/export",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Event not found"}
    }
)
async def export_attendees_csv(
    event_id: str,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db)
):
    """
    Export attendees list as CSV file.
    
    **Business Rules:**
    - Only event owner or admin can export
    - Exports all confirmed registrations
    - Includes guest information
    
    **Path Parameters:**
    - event_id: Event ID
    
    **Returns:**
    - CSV file download with columns:
      - Name, Email, Registration Date, Ticket Code
      - Check-in Status, Checked-in At
      - Guest Count, Guest Names
    """
    organizer_service = OrganizerService(db)
    
    try:
        csv_content = organizer_service.export_attendees_csv(
            event_id=event_id,
            organizer=current_user
        )
        
        # Return as streaming response with CSV content type
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=attendees_{event_id}.csv"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export attendees: {str(e)}"
        )


@router.post(
    "/events/{event_id}/check-in/{registration_id}",
    response_model=CheckInResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Already checked in or invalid registration"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Event or registration not found"}
    }
)
async def check_in_attendee(
    event_id: str,
    registration_id: str,
    request: Request,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db)
):
    """
    Check-in an attendee.
    
    **Business Rules:**
    - Only event owner or admin can check-in attendees
    - Registration must be for the specified event
    - Registration must be confirmed (not cancelled)
    - Cannot check-in already checked-in attendee
    
    **Path Parameters:**
    - event_id: Event ID
    - registration_id: Registration ID to check-in
    
    **Returns:**
    - Updated registration with check-in timestamp
    """
    ip_address, user_agent = get_client_info(request)
    
    organizer_service = OrganizerService(db)
    
    try:
        registration = organizer_service.check_in_attendee(
            event_id=event_id,
            registration_id=registration_id,
            organizer=current_user,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return CheckInResponse(
            success=True,
            message="Attendee checked in successfully",
            registration={
                "id": registration.id,
                "ticketCode": registration.ticket_code,
                "checkInStatus": registration.check_in_status.value,
                "checkedInAt": registration.checked_in_at.isoformat() if registration.checked_in_at else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check-in attendee: {str(e)}"
        )


# ============================================
# Communication (2 APIs)
# ============================================

@router.post(
    "/events/{event_id}/announcements",
    response_model=AnnouncementResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Event not found"}
    }
)
async def send_announcement(
    event_id: str,
    announcement: AnnouncementCreate,
    request: Request,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db)
):
    """
    Send announcement to all registered attendees.
    
    **Business Rules:**
    - Only event owner or admin can send announcements
    - Sends to all confirmed registrations
    - Includes guests with email addresses
    
    **Path Parameters:**
    - event_id: Event ID
    
    **Request Body:**
    - subject: Announcement subject (5-200 characters)
    - message: Announcement message (10-5000 characters)
    
    **Returns:**
    - Success message with recipient count
    """
    ip_address, user_agent = get_client_info(request)
    
    organizer_service = OrganizerService(db)
    
    try:
        result = organizer_service.send_announcement(
            event_id=event_id,
            subject=announcement.subject,
            message=announcement.message,
            organizer=current_user,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return AnnouncementResponse(
            success=True,
            message=result["message"],
            recipientCount=result["recipientCount"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send announcement: {str(e)}"
        )


@router.get(
    "/events/{event_id}/waitlist",
    response_model=EventWaitlistResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Event not found"}
    }
)
async def get_event_waitlist(
    event_id: str,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db)
):
    """
    View waitlist for an event.
    
    **Business Rules:**
    - Only event owner or admin can view waitlist
    - Returns entries sorted by position (FIFO order)
    
    **Path Parameters:**
    - event_id: Event ID
    
    **Returns:**
    - List of waitlist entries with:
      - Position, Name, Email
      - Join time, Notification preference
    - Total count
    """
    organizer_service = OrganizerService(db)
    
    try:
        waitlist = organizer_service.get_event_waitlist(
            event_id=event_id,
            organizer=current_user
        )
        
        # Convert to response format
        waitlist_responses = [
            WaitlistEntryInfo(
                id=entry["id"],
                userId=entry["userId"],
                position=entry["position"],
                name=entry["name"],
                email=entry["email"],
                joinedAt=entry["joinedAt"] or "",
                notificationPreference=entry["notificationPreference"]
            )
            for entry in waitlist
        ]
        
        return EventWaitlistResponse(
            success=True,
            waitlist=waitlist_responses,
            totalCount=len(waitlist_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve waitlist: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for organizer API.
    
    **Returns:**
    - API status and version
    """
    return {
        "status": "healthy",
        "service": "TerpSpark Organizer API",
        "version": "1.0.0",
        "phase": "Phase 4: Organizer Management"
    }


