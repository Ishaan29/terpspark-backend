from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.registration_service import RegistrationService
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.schemas.waitlist import (
    WaitlistCreate,
    WaitlistCreateResponse,
    WaitlistResponse,
    WaitlistListResponse,
    EventWaitlistInfo
)
from app.schemas.auth import ErrorResponse

router = APIRouter(prefix="/api/waitlist", tags=["Waitlist"])


@router.post(
    "",
    response_model=WaitlistCreateResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Event not found"},
        409: {"model": ErrorResponse, "description": "Already registered or on waitlist"},
        400: {"model": ErrorResponse, "description": "Event not full"}
    }
)
async def join_waitlist(
    waitlist_data: WaitlistCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Join waitlist for a full event.

    **Authentication Required:** Yes (must be logged in)

    **Request Body:**
    ```json
    {
        "eventId": "event-uuid",
        "notificationPreference": "email"
    }
    ```

    **Success Response (200):**
    ```json
    {
        "success": true,
        "message": "Added to waitlist at position 5",
        "waitlistEntry": {
            "id": "waitlist-uuid",
            "userId": "user-uuid",
            "eventId": "event-uuid",
            "position": 5,
            "joinedAt": "2025-11-26T10:30:00Z",
            "notificationPreference": "email"
        }
    }
    ```

    **Business Rules:**
    - Can only join waitlist if event is full
    - Position assigned based on join order (FIFO)
    - Cannot join if already registered or on waitlist
    - Notification sent to user with their position
    """
    # Initialize registration service
    registration_service = RegistrationService(db)

    try:
        # Join waitlist (all business logic in service)
        waitlist_entry = registration_service.join_waitlist(
            user_id=current_user.id,
            waitlist_data=waitlist_data
        )

        # Convert to response format
        waitlist_response = WaitlistResponse(
            id=waitlist_entry.id,
            userId=waitlist_entry.user_id,
            eventId=waitlist_entry.event_id,
            position=waitlist_entry.position,
            joinedAt=waitlist_entry.joined_at.isoformat(),
            notificationPreference=waitlist_entry.notification_preference.value,
            event=None  # Not included in creation response
        )

        return WaitlistCreateResponse(
            success=True,
            message=f"Added to waitlist at position {waitlist_entry.position}",
            waitlistEntry=waitlist_response
        )

    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to join waitlist: {str(e)}"
        )


@router.get(
    "",
    response_model=WaitlistListResponse,
    status_code=status.HTTP_200_OK
)
async def get_user_waitlist(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's waitlist entries.

    **Authentication Required:** Yes (must be logged in)

    **Success Response (200):**
    ```json
    {
        "success": true,
        "waitlist": [
            {
                "id": "waitlist-uuid",
                "userId": "user-uuid",
                "eventId": "event-uuid",
                "event": {
                    "id": "event-uuid",
                    "title": "AI & Machine Learning Workshop",
                    "date": "2025-12-03",
                    "capacity": 100,
                    "registeredCount": 100
                },
                "position": 3,
                "joinedAt": "2025-11-26T10:30:00Z",
                "notificationPreference": "email"
            }
        ]
    }
    ```

    **Business Rules:**
    - Returns only current user's waitlist entries
    - Sorted by join date (oldest first)
    """
    registration_service = RegistrationService(db)

    try:
        waitlist_entries = registration_service.get_user_waitlist(
            user_id=current_user.id
        )

        waitlist_responses = []
        for entry in waitlist_entries:
            event_info = None
            if entry.event:
                event_info = EventWaitlistInfo(
                    id=entry.event.id,
                    title=entry.event.title,
                    date=entry.event.date.isoformat() if entry.event.date else "",
                    capacity=entry.event.capacity,
                    registeredCount=entry.event.registered_count
                )

            waitlist_response = WaitlistResponse(
                id=entry.id,
                userId=entry.user_id,
                eventId=entry.event_id,
                position=entry.position,
                joinedAt=entry.joined_at.isoformat(),
                notificationPreference=entry.notification_preference.value,
                event=event_info
            )
            waitlist_responses.append(waitlist_response)

        return WaitlistListResponse(
            success=True,
            waitlist=waitlist_responses
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve waitlist: {str(e)}"
        )


@router.delete(
    "/{waitlist_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Waitlist entry not found"},
        403: {"model": ErrorResponse, "description": "Not authorized"}
    }
)
async def leave_waitlist(
    waitlist_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Leave waitlist for an event.

    **Authentication Required:** Yes (must be logged in)

    **Path Parameters:**
    - `waitlist_id`: The ID of the waitlist entry to remove

    **Success Response (200):**
    ```json
    {
        "success": true,
        "message": "Removed from waitlist successfully"
    }
    ```

    **Business Rules:**
    - Can only remove own waitlist entry
    - Positions updated for remaining members
    - Event's waitlistCount decreased
    """
    # Initialize registration service
    registration_service = RegistrationService(db)

    try:
        # Leave waitlist (all business logic in service)
        removed_entry = registration_service.leave_waitlist(
            waitlist_id=waitlist_id,
            user_id=current_user.id
        )

        return {
            "success": True,
            "message": "Removed from waitlist successfully"
        }

    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to leave waitlist: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """
    Health check endpoint for waitlist API.

    **Returns:**
    - API status and version
    """
    return {
        "status": "healthy",
        "service": "TerpSpark Waitlist API",
        "version": "1.0.0",
        "phase": "Phase 3: Student Registration Flow"
    }
