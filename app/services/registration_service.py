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
from app.repositories.waitlist_repository import WaitlistRepository
from app.models.registration import Registration, RegistrationStatus
from app.models.event import Event, EventStatus
from app.models.audit_log import AuditAction, TargetType
from app.models.waitlist import WaitlistEntry, NotificationPreference
from app.schemas.registration import RegistrationCreate
from app.schemas.waitlist import WaitlistCreate
from app.utils.qr_generator import generate_qr_code, generate_ticket_code
from app.utils.email_service import EmailService


class RegistrationService:

    def __init__(self, db: Session):
        self.db = db
        self.registration_repo = RegistrationRepository(db)
        self.event_repo = EventRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditLogRepository(db)
        self.waitlist_repo = WaitlistRepository(db)
        self.email_service = EmailService(db)

    def create_registration(
        self,
        user_id: str,
        registration_data: RegistrationCreate
    ) -> Registration:
        event = self.db.query(Event).filter(
            Event.id == registration_data.eventId
        ).with_for_update().first()

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        if event.status != EventStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event is not published. Current status: {event.status.value}"
            )

        if event.date and event.date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot register for past events"
            )

        existing_registration = self.registration_repo.get_by_user_and_event(
            user_id=user_id,
            event_id=registration_data.eventId
        )
        if existing_registration:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You are already registered for this event"
            )

        guests = registration_data.guests or []
        if len(guests) > 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Maximum 2 guests allowed per registration"
            )

        for guest in guests:
            guest_email_lower = guest.email.lower()
            if not (guest_email_lower.endswith('@umd.edu') or guest_email_lower.endswith('@terpmail.umd.edu')):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Guest email {guest.email} must be a valid UMD email (@umd.edu or @terpmail.umd.edu)"
                )

        guest_emails = [g.email.lower() for g in guests]
        if len(guest_emails) != len(set(guest_emails)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Duplicate guest emails are not allowed"
            )

        for guest in guests:
            guest_user = self.user_repo.get_by_email(guest.email)
            if guest_user:
                guest_registration = self.registration_repo.get_by_user_and_event(
                    user_id=guest_user.id,
                    event_id=registration_data.eventId
                )
                if guest_registration and guest_registration.status == RegistrationStatus.CONFIRMED:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Guest {guest.email} is already registered for this event as a primary attendee"
                    )

            all_event_registrations = self.registration_repo.get_event_registrations(
                event_id=registration_data.eventId,
                status=RegistrationStatus.CONFIRMED
            )
            for reg in all_event_registrations:
                if reg.guests:
                    guest_emails_in_reg = [g.get('email', '').lower() for g in reg.guests]
                    if guest.email.lower() in guest_emails_in_reg:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Guest {guest.email} is already registered for this event as a guest of another attendee"
                        )

        total_attendees_needed = 1 + len(guests)
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

        guests_data = [{"name": g.name, "email": g.email} for g in guests] if guests else []

        registration = self.registration_repo.create(
            user_id=user_id,
            event_id=registration_data.eventId,
            ticket_code=ticket_code,
            qr_code=qr_code,
            guests=guests_data,
            sessions=registration_data.sessions or []
        )

        event.registered_count += total_attendees_needed
        self.event_repo.update(event)

        user = self.user_repo.get_by_id(user_id)

        try:
            self.email_service.send_registration_confirmation(
                user=user,
                event=event,
                registration=registration
            )
        except Exception as e:
            print(f"Warning: Failed to send confirmation email: {str(e)}")

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
            ip_address=None,
            user_agent=None
        )

        self.db.commit()

        self.db.refresh(registration)

        return registration

    def get_user_registrations(
        self,
        user_id: str,
        status_filter: str = "confirmed",
        include_past: bool = False
    ) -> list[Registration]:
        status_enum = None
        if status_filter == "confirmed":
            status_enum = RegistrationStatus.CONFIRMED
        elif status_filter == "cancelled":
            status_enum = RegistrationStatus.CANCELLED
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
        registration = self.registration_repo.get_by_id(registration_id, include_relations=True)

        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found"
            )

        if registration.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own registrations"
            )

        if registration.status == RegistrationStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration is already cancelled"
            )

        guests_count = len(registration.guests) if registration.guests else 0
        total_attendees = 1 + guests_count

        cancelled_registration = self.registration_repo.cancel(registration)

        event = self.event_repo.get_by_id(registration.event_id)
        if event:
            event.registered_count -= total_attendees
            if event.registered_count < 0:
                event.registered_count = 0
            self.event_repo.update(event)

        user = self.user_repo.get_by_id(user_id)
        try:
            self.email_service.send_cancellation_confirmation(
                user=user,
                event=event,
                registration=cancelled_registration
            )
        except Exception as e:
            print(f"Warning: Failed to send cancellation email: {str(e)}")

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

        try:
            promoted = self.promote_from_waitlist(event.id)
            if promoted:
                print(f"Successfully promoted someone from waitlist for event {event.title}")
        except Exception as e:
            print(f"Warning: Failed to promote from waitlist: {str(e)}")

        self.db.commit()
        self.db.refresh(cancelled_registration)

        return cancelled_registration

    def join_waitlist(
        self,
        user_id: str,
        waitlist_data: WaitlistCreate
    ) -> WaitlistEntry:
        event = self.event_repo.get_by_id(waitlist_data.eventId)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        if event.status != EventStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event is not published"
            )
        existing_registration = self.registration_repo.get_by_user_and_event(
            user_id=user_id,
            event_id=waitlist_data.eventId
        )
        if existing_registration:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You are already registered for this event"
            )

        existing_waitlist = self.waitlist_repo.get_by_user_and_event(
            user_id=user_id,
            event_id=waitlist_data.eventId
        )
        if existing_waitlist:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You are already on the waitlist for this event"
            )
        if event.registered_count < event.capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event is not full. {event.capacity - event.registered_count} spot(s) available. Please register instead."
            )

        pref_map = {
            "email": NotificationPreference.EMAIL,
            "sms": NotificationPreference.SMS,
            "both": NotificationPreference.BOTH
        }
        notification_pref = pref_map.get(
            waitlist_data.notificationPreference.lower(),
            NotificationPreference.EMAIL
        )

        waitlist_entry = self.waitlist_repo.create(
            user_id=user_id,
            event_id=waitlist_data.eventId,
            notification_preference=notification_pref
        )

        event.waitlist_count += 1
        self.event_repo.update(event)

        user = self.user_repo.get_by_id(user_id)
        try:
            self.email_service.send_waitlist_confirmation(
                user=user,
                event=event,
                position=waitlist_entry.position
            )
        except Exception as e:
            print(f"Warning: Failed to send waitlist confirmation email: {str(e)}")

        self.audit_repo.create(
            action=AuditAction.WAITLIST_JOINED,
            actor_id=user_id,
            actor_name=user.name,
            actor_role=user.role.value,
            target_type=TargetType.EVENT,
            target_id=event.id,
            target_name=event.title,
            details=f"User {user.name} joined waitlist for {event.title} at position {waitlist_entry.position}",
            ip_address=None,
            user_agent=None
        )

        self.db.commit()
        self.db.refresh(waitlist_entry)

        return waitlist_entry

    def get_user_waitlist(self, user_id: str) -> list[WaitlistEntry]:
        return self.waitlist_repo.get_user_waitlist_entries(user_id)

    def leave_waitlist(
        self,
        waitlist_id: str,
        user_id: str
    ) -> WaitlistEntry:
        waitlist_entry = self.waitlist_repo.get_by_id(waitlist_id, include_relations=True)

        if not waitlist_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waitlist entry not found"
            )

        if waitlist_entry.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only remove your own waitlist entries"
            )

        event = self.event_repo.get_by_id(waitlist_entry.event_id)

        self.waitlist_repo.remove(waitlist_entry)

        if event:
            event.waitlist_count -= 1
            if event.waitlist_count < 0:
                event.waitlist_count = 0
            self.event_repo.update(event)

        user = self.user_repo.get_by_id(user_id)
        self.audit_repo.create(
            action=AuditAction.WAITLIST_LEFT,
            actor_id=user_id,
            actor_name=user.name,
            actor_role=user.role.value,
            target_type=TargetType.EVENT,
            target_id=event.id if event else waitlist_entry.event_id,
            target_name=event.title if event else "Unknown Event",
            details=f"User {user.name} left waitlist for {event.title if event else 'event'}",
            ip_address=None,
            user_agent=None
        )

        self.db.commit()

        return waitlist_entry

    def promote_from_waitlist(self, event_id: str) -> bool:
        waitlist_entry = self.waitlist_repo.get_first_in_line(event_id)

        if not waitlist_entry:
            return False

        event = self.event_repo.get_by_id(event_id)
        user = self.user_repo.get_by_id(waitlist_entry.user_id)

        if not event or not user:
            return False

        existing_registration = self.registration_repo.get_by_user_and_event(
            user_id=user.id,
            event_id=event_id
        )
        if existing_registration and existing_registration.status == RegistrationStatus.CONFIRMED:
            self.waitlist_repo.remove(waitlist_entry)
            event.waitlist_count -= 1
            if event.waitlist_count < 0:
                event.waitlist_count = 0
            self.event_repo.update(event)
            self.db.commit()
            return False

        timestamp = int(time.time())
        ticket_code = generate_ticket_code(timestamp, event.id)

        existing_ticket = self.db.query(Registration).filter(
            Registration.ticket_code == ticket_code
        ).first()
        if existing_ticket:
            ticket_code = f"{ticket_code}-{uuid.uuid4().hex[:4]}"

        qr_code = generate_qr_code(ticket_code)

        registration = self.registration_repo.create(
            user_id=user.id,
            event_id=event.id,
            ticket_code=ticket_code,
            qr_code=qr_code,
            guests=[],
            sessions=[]
        )

        event.registered_count += 1
        self.event_repo.update(event)

        old_position = waitlist_entry.position
        try:
            self.email_service.send_waitlist_promotion(
                user=user,
                event=event,
                registration=registration,
                old_position=old_position
            )
        except Exception as e:
            print(f"Warning: Failed to send waitlist promotion email: {str(e)}")

        self.waitlist_repo.remove(waitlist_entry)

        event.waitlist_count -= 1
        if event.waitlist_count < 0:
            event.waitlist_count = 0
        self.event_repo.update(event)

        self.audit_repo.create(
            action=AuditAction.WAITLIST_PROMOTED,
            actor_id=user.id,
            actor_name=user.name,
            actor_role=user.role.value,
            target_type=TargetType.REGISTRATION,
            target_id=registration.id,
            target_name=event.title,
            details=f"User {user.name} promoted from waitlist position {old_position} to confirmed registration for {event.title}",
            ip_address=None,
            user_agent=None
        )

        self.db.commit()

        return True
