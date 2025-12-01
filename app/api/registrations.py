"""
Registration API routes for Phase 3: Student Registration Flow.
Handles event registration, cancellation, and waitlist management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.registration_service import RegistrationService
from app.middleware.auth import get_current_active_user
from app.models.user import User
from app.schemas.registration import (
    RegistrationCreate,
    RegistrationCreateResponse,
    RegistrationResponse,
    RegistrationsListResponse,
    EventBasicInfo
)
from app.schemas.auth import ErrorResponse

# Create router with prefix and tags
router = APIRouter(prefix="/api/registrations", tags=["Registrations"])


@router.post(
    "",
    response_model=RegistrationCreateResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Event not found"},
        409: {"model": ErrorResponse, "description": "Already registered or event full"},
        422: {"model": ErrorResponse, "description": "Validation error"}
    }
)
async def register_for_event(
    registration_data: RegistrationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Register current user for an event.

    **Authentication Required:** Yes (must be logged in)

    **Business Rules:**
    - User must be authenticated
    - Event must exist and be published
    - Event date must be in future
    - User cannot already be registered for this event
    - Maximum 2 guests allowed
    - Guest emails must be @umd.edu
    - Total capacity (user + guests) must be available
    - Generates unique ticket code and QR code
    - Sends confirmation email to user

    **Request Body:**
    ```json
    {
        "eventId": "event-uuid",
        "guests": [
            {
                "name": "John Doe",
                "email": "john.doe@umd.edu"
            }
        ],
        "notificationPreference": "email"
    }
    ```

    **Success Response (200):**
    ```json
    {
        "success": true,
        "message": "Successfully registered for event",
        "registration": {
            "id": "registration-uuid",
            "userId": "user-uuid",
            "eventId": "event-uuid",
            "status": "confirmed",
            "ticketCode": "TKT-1732635421-abc123",
            "qrCode": "data:image/png;base64,...",
            "registeredAt": "2025-11-26T10:30:00Z",
            "checkInStatus": "not_checked_in",
            "guests": [...],
            "sessions": [],
            "reminderSent": false
        }
    }
    ```

    **Error Responses:**
    - 404: Event not found
    - 400: Event not published or in past
    - 409: Already registered OR Event is full
    - 422: Invalid guest emails or too many guests
    """
    # Initialize registration service
    registration_service = RegistrationService(db)

    try:
        # Create registration (all business logic in service)
        registration = registration_service.create_registration(
            user_id=current_user.id,
            registration_data=registration_data
        )

        # Convert to response format
        registration_response = RegistrationResponse(
            id=registration.id,
            userId=registration.user_id,
            eventId=registration.event_id,
            status=registration.status.value,
            ticketCode=registration.ticket_code,
            qrCode=registration.qr_code,
            registeredAt=registration.registered_at.isoformat(),
            checkInStatus=registration.check_in_status.value,
            checkedInAt=registration.checked_in_at.isoformat() if registration.checked_in_at else None,
            guests=registration.guests if registration.guests else [],
            sessions=registration.sessions if registration.sessions else [],
            reminderSent=registration.reminder_sent,
            cancelledAt=registration.cancelled_at.isoformat() if registration.cancelled_at else None,
            event=None  # Not included in creation response
        )

        # Return success response
        return RegistrationCreateResponse(
            success=True,
            message="Successfully registered for event",
            registration=registration_response
        )

    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.get(
    "",
    response_model=RegistrationsListResponse,
    status_code=status.HTTP_200_OK
)
async def get_user_registrations(
    status: str = "confirmed",
    include_past: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's registrations.

    **Authentication Required:** Yes (must be logged in)

    **Query Parameters:**
    - `status`: Filter by status - 'confirmed', 'cancelled', or 'all' (default: 'confirmed')
    - `include_past`: Include past events (default: false)

    **Success Response (200):**
    ```json
    {
        "success": true,
        "registrations": [
            {
                "id": "registration-uuid",
                "userId": "user-uuid",
                "eventId": "event-uuid",
                "event": {
                    "id": "event-uuid",
                    "title": "AI & Machine Learning Workshop",
                    "date": "2025-12-03",
                    "startTime": "14:00",
                    "endTime": "17:00",
                    "venue": "Engineering Building",
                    "organizer": {
                        "name": "Tech Club"
                    }
                },
                "status": "confirmed",
                "ticketCode": "TKT-1732635421-abc123",
                "qrCode": "data:image/png;base64,...",
                "registeredAt": "2025-11-26T10:30:00Z",
                "checkInStatus": "not_checked_in",
                "checkedInAt": null,
                "guests": [
                    {
                        "name": "John Doe",
                        "email": "john.doe@umd.edu"
                    }
                ],
                "sessions": [],
                "reminderSent": false,
                "cancelledAt": null
            }
        ]
    }
    ```

    **Business Rules:**
    - Returns only current user's registrations
    - Filters by status (confirmed/cancelled/all)
    - By default excludes past events
    - Sorted by event date (upcoming first)
    """
    # Validate status parameter
    if status not in ["confirmed", "cancelled", "all"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status parameter. Must be 'confirmed', 'cancelled', or 'all'"
        )

    # Initialize registration service
    registration_service = RegistrationService(db)

    try:
        # Get user's registrations
        registrations = registration_service.get_user_registrations(
            user_id=current_user.id,
            status_filter=status,
            include_past=include_past
        )

        # Convert to response format
        registration_responses = []
        for reg in registrations:
            # Build event basic info
            event_info = None
            if reg.event:
                event_info = EventBasicInfo(
                    id=reg.event.id,
                    title=reg.event.title,
                    date=reg.event.date.isoformat() if reg.event.date else "",
                    startTime=reg.event.start_time.strftime('%H:%M') if reg.event.start_time else "",
                    endTime=reg.event.end_time.strftime('%H:%M') if reg.event.end_time else "",
                    venue=reg.event.venue,
                    organizer={
                        "name": reg.event.organizer.name if reg.event.organizer else ""
                    }
                )

            registration_response = RegistrationResponse(
                id=reg.id,
                userId=reg.user_id,
                eventId=reg.event_id,
                status=reg.status.value,
                ticketCode=reg.ticket_code,
                qrCode=reg.qr_code,
                registeredAt=reg.registered_at.isoformat(),
                checkInStatus=reg.check_in_status.value,
                checkedInAt=reg.checked_in_at.isoformat() if reg.checked_in_at else None,
                guests=reg.guests if reg.guests else [],
                sessions=reg.sessions if reg.sessions else [],
                reminderSent=reg.reminder_sent,
                cancelledAt=reg.cancelled_at.isoformat() if reg.cancelled_at else None,
                event=event_info
            )
            registration_responses.append(registration_response)

        return RegistrationsListResponse(
            success=True,
            registrations=registration_responses
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve registrations: {str(e)}"
        )


@router.delete(
    "/{registration_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Registration not found"},
        403: {"model": ErrorResponse, "description": "Not authorized to cancel this registration"},
        400: {"model": ErrorResponse, "description": "Registration already cancelled"}
    }
)
async def cancel_registration(
    registration_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a registration.

    **Authentication Required:** Yes (must be logged in)

    **Path Parameters:**
    - `registration_id`: The ID of the registration to cancel

    **Success Response (200):**
    ```json
    {
        "success": true,
        "message": "Registration cancelled successfully"
    }
    ```

    **Error Responses:**
    - 404: Registration not found
    - 403: You can only cancel your own registrations
    - 400: Registration is already cancelled

    **Business Rules:**
    - Can only cancel own registration
    - Marks registration as cancelled (doesn't delete)
    - Decreases event's registeredCount by (1 + number of guests)
    - Sends cancellation confirmation email
    - TODO: Auto-promotes first person from waitlist (after waitlist APIs implemented)
    """
    # Initialize registration service
    registration_service = RegistrationService(db)

    try:
        # Cancel the registration (all business logic in service)
        cancelled_registration = registration_service.cancel_registration(
            registration_id=registration_id,
            user_id=current_user.id
        )

        # Return success response
        return {
            "success": True,
            "message": "Registration cancelled successfully"
        }

    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel registration: {str(e)}"
        )


# Health check endpoint for registration API
@router.get("/health")
async def health_check():
    """
    Health check endpoint for registration API.

    **Returns:**
    - API status and version
    """
    return {
        "status": "healthy",
        "service": "TerpSpark Registration API",
        "version": "1.0.0",
        "phase": "Phase 3: Student Registration Flow"
    }
