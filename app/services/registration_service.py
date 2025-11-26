"""
Registration Service - Business logic for event registrations and waitlist management.
Handles registration creation, capacity management, and waitlist promotions.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Tuple
from datetime import date
import time
import uuid

from app.repositories.registration_repository import RegistrationRepository
from app.repositories.event_repository import EventRepository
from app.repositories.user_repository import UserRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.models.registration import Registration, RegistrationStatus
from app.models.event import Event, EventStatus
from app.models.audit_log import AuditAction, TargetType
from app.schemas.registration import RegistrationCreate
from app.utils.qr_generator import generate_qr_code, generate_ticket_code
from app.utils.email_service import EmailService


class RegistrationService:
    """Service for managing event registrations and waitlist."""

    def __init__(self, db: Session):
        """
        Initialize registration service with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.registration_repo = RegistrationRepository(db)
        self.event_repo = EventRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditLogRepository(db)
        self.email_service = EmailService(db)

    def create_registration(
        self,
        user_id: str,
        registration_data: RegistrationCreate
    ) -> Registration:
        """
        Create a new registration for an event.

        BUSINESS LOGIC:
        1. Validate event exists and is published
        2. Check event date is in future
        3. Check for duplicate registration
        4. Validate guests (max 2, must be @umd.edu)
        5. Check capacity (user + guests must fit)
        6. Generate unique ticket code
        7. Generate QR code
        8. Create registration record
        9. Update event registered_count
        10. Send confirmation email
        11. Log to audit trail

        Args:
            user_id: ID of user registering
            registration_data: Registration details including event_id and guests

        Returns:
            Registration: The created registration with ticket and QR code

        Raises:
            HTTPException 404: Event not found
            HTTPException 400: Event not published or in past
            HTTPException 409: Already registered or insufficient capacity
            HTTPException 422: Validation errors (guest emails, etc.)
        """
        # ====================================================================
        # STEP 1: GET AND VALIDATE EVENT
        # ====================================================================
        event = self.event_repo.get_by_id(registration_data.eventId)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        # Check event status - must be published
        if event.status != EventStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event is not published. Current status: {event.status.value}"
            )

        # Check event date - must be in future
        if event.date and event.date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot register for past events"
            )

        # ====================================================================
        # STEP 2: CHECK FOR DUPLICATE REGISTRATION
        # ====================================================================
        existing_registration = self.registration_repo.get_by_user_and_event(
            user_id=user_id,
            event_id=registration_data.eventId
        )
        if existing_registration:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You are already registered for this event"
            )

        # ====================================================================
        # STEP 3: VALIDATE GUESTS
        # ====================================================================
        guests = registration_data.guests or []
        if len(guests) > 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Maximum 2 guests allowed per registration"
            )

        # Validate guest emails
        for guest in guests:
            if not guest.email.lower().endswith('@umd.edu'):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Guest email {guest.email} must be a valid UMD email (@umd.edu)"
                )

        # Check for duplicate guest emails within this registration
        guest_emails = [g.email.lower() for g in guests]
        if len(guest_emails) != len(set(guest_emails)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Duplicate guest emails are not allowed"
            )

        # Check if any guest is already registered (as main attendee)
        for guest in guests:
            guest_registration = self.registration_repo.get_by_user_and_event(
                user_id=guest.email,  # Simplified check
                event_id=registration_data.eventId
            )
            # Note: More robust check would query by email across all users
            # For now, this is a simplified version

        # ====================================================================
        # STEP 4: CHECK CAPACITY
        # ====================================================================
        total_attendees_needed = 1 + len(guests)  # User + guests
        remaining_capacity = event.capacity - event.registered_count

        if remaining_capacity < total_attendees_needed:
            if remaining_capacity == 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Event is full. Please join the waitlist instead.",
                    headers={"X-Suggestion": "join-waitlist"}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Insufficient capacity. Only {remaining_capacity} spot(s) remaining, but you need {total_attendees_needed} (including guests). Please reduce guests or join waitlist."
                )

        # ====================================================================
        # STEP 5: GENERATE TICKET CODE AND QR CODE
        # ====================================================================
        timestamp = int(time.time())
        ticket_code = generate_ticket_code(timestamp, event.id)

        # Ensure ticket code is unique (very unlikely collision, but check anyway)
        existing_ticket = self.db.query(Registration).filter(
            Registration.ticket_code == ticket_code
        ).first()
        if existing_ticket:
            # Add milliseconds to make it unique
            ticket_code = f"{ticket_code}-{uuid.uuid4().hex[:4]}"

        # Generate QR code from ticket code
        qr_code = generate_qr_code(ticket_code)

        # ====================================================================
        # STEP 6: CREATE REGISTRATION IN DATABASE
        # ====================================================================
        # Convert guests to dict format for JSON storage
        guests_data = [{"name": g.name, "email": g.email} for g in guests] if guests else []

        registration = self.registration_repo.create(
            user_id=user_id,
            event_id=registration_data.eventId,
            ticket_code=ticket_code,
            qr_code=qr_code,
            guests=guests_data,
            sessions=registration_data.sessions or []
        )

        # ====================================================================
        # STEP 7: UPDATE EVENT REGISTERED COUNT
        # ====================================================================
        event.registered_count += total_attendees_needed
        self.event_repo.update(event)

        # ====================================================================
        # STEP 8: GET USER FOR EMAIL
        # ====================================================================
        user = self.user_repo.get_by_id(user_id)

        # ====================================================================
        # STEP 9: SEND CONFIRMATION EMAIL
        # ====================================================================
        try:
            self.email_service.send_registration_confirmation(
                user=user,
                event=event,
                registration=registration
            )
        except Exception as e:
            # Log email error but don't fail the registration
            print(f"Warning: Failed to send confirmation email: {str(e)}")

        # ====================================================================
        # STEP 10: CREATE AUDIT LOG
        # ====================================================================
        guests_info = f" with {len(guests)} guest(s)" if guests else ""
        self.audit_repo.create(
            action=AuditAction.REGISTRATION_CREATED,
            actor_id=user_id,
            actor_name=user.name,
            actor_role=user.role.value,
            target_type=TargetType.REGISTRATION,
            target_id=registration.id,
            target_name=event.title,
            details=f"User {user.name} registered for {event.title}{guests_info}",
            ip_address=None,  # Can be added later from request
            user_agent=None
        )

        # Commit all changes
        self.db.commit()

        # Refresh to get relationships
        self.db.refresh(registration)

        return registration

    def get_user_registrations(
        self,
        user_id: str,
        status_filter: str = "confirmed",
        include_past: bool = False
    ) -> list[Registration]:
        """
        Get all registrations for a user with filtering.

        Args:
            user_id: ID of the user
            status_filter: Filter by status - 'confirmed', 'cancelled', or 'all'
            include_past: Whether to include past events (default: False)

        Returns:
            list[Registration]: List of user's registrations

        Business Logic:
        - Filter by status if not 'all'
        - Exclude past events unless include_past=True
        - Return registrations with event details loaded
        - Sort by event date (upcoming first)
        """
        # Convert status filter string to enum
        status_enum = None
        if status_filter == "confirmed":
            status_enum = RegistrationStatus.CONFIRMED
        elif status_filter == "cancelled":
            status_enum = RegistrationStatus.CANCELLED
        # If 'all', status_enum stays None (no filter)

        # Get registrations from repository
        registrations = self.registration_repo.get_user_registrations(
            user_id=user_id,
            status=status_enum,
            include_past=include_past
        )

        return registrations

    def cancel_registration(
        self,
        registration_id: str,
        user_id: str
    ) -> Registration:
        """
        Cancel a registration.

        BUSINESS LOGIC:
        1. Validate registration exists
        2. Check user owns the registration
        3. Check if already cancelled
        4. Mark registration as cancelled
        5. Decrease event registered_count (user + guests)
        6. Send cancellation email
        7. Create audit log
        8. TODO: Auto-promote from waitlist (Phase 3 - after waitlist APIs)

        Args:
            registration_id: ID of registration to cancel
            user_id: ID of user requesting cancellation

        Returns:
            Registration: The cancelled registration

        Raises:
            HTTPException 404: Registration not found
            HTTPException 403: User doesn't own this registration
            HTTPException 400: Registration already cancelled
        """
        # ====================================================================
        # STEP 1: GET AND VALIDATE REGISTRATION
        # ====================================================================
        registration = self.registration_repo.get_by_id(registration_id, include_relations=True)

        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found"
            )

        # ====================================================================
        # STEP 2: CHECK OWNERSHIP
        # ====================================================================
        if registration.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own registrations"
            )

        # ====================================================================
        # STEP 3: CHECK IF ALREADY CANCELLED
        # ====================================================================
        if registration.status == RegistrationStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration is already cancelled"
            )

        # ====================================================================
        # STEP 4: CALCULATE CAPACITY TO FREE
        # ====================================================================
        # Count user + guests
        guests_count = len(registration.guests) if registration.guests else 0
        total_attendees = 1 + guests_count  # User + guests

        # ====================================================================
        # STEP 5: MARK AS CANCELLED
        # ====================================================================
        cancelled_registration = self.registration_repo.cancel(registration)

        # ====================================================================
        # STEP 6: UPDATE EVENT REGISTERED COUNT
        # ====================================================================
        event = self.event_repo.get_by_id(registration.event_id)
        if event:
            event.registered_count -= total_attendees
            # Ensure it doesn't go negative
            if event.registered_count < 0:
                event.registered_count = 0
            self.event_repo.update(event)

        # ====================================================================
        # STEP 7: SEND CANCELLATION EMAIL
        # ====================================================================
        user = self.user_repo.get_by_id(user_id)
        try:
            self.email_service.send_cancellation_confirmation(
                user=user,
                event=event,
                registration=cancelled_registration
            )
        except Exception as e:
            # Log email error but don't fail the cancellation
            print(f"Warning: Failed to send cancellation email: {str(e)}")

        # ====================================================================
        # STEP 8: CREATE AUDIT LOG
        # ====================================================================
        self.audit_repo.create(
            action=AuditAction.REGISTRATION_CANCELLED,
            actor_id=user_id,
            actor_name=user.name,
            actor_role=user.role.value,
            target_type=TargetType.REGISTRATION,
            target_id=registration.id,
            target_name=event.title if event else "Unknown Event",
            details=f"User {user.name} cancelled registration for {event.title if event else 'event'}. Freed {total_attendees} spot(s).",
            ip_address=None,
            user_agent=None
        )

        # ====================================================================
        # STEP 9: TODO - AUTO-PROMOTE FROM WAITLIST
        # ====================================================================
        # TODO: After implementing waitlist APIs, add logic to:
        # 1. Check if event has waitlist entries
        # 2. Get first person from waitlist (lowest position)
        # 3. Create registration for them
        # 4. Remove from waitlist
        # 5. Update waitlist positions
        # 6. Send promotion notification email

        # Commit all changes
        self.db.commit()
        self.db.refresh(cancelled_registration)

        return cancelled_registration
