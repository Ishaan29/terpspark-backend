from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import date, datetime
import uuid
import csv
import io
import logging

logger = logging.getLogger(__name__)

from app.models.event import Event, EventStatus
from app.models.user import User, UserRole
from app.models.registration import Registration, RegistrationStatus, CheckInStatus
from app.models.waitlist import WaitlistEntry
from app.models.audit_log import AuditAction, TargetType
from app.repositories.event_repository import EventRepository
from app.repositories.registration_repository import RegistrationRepository
from app.repositories.waitlist_repository import WaitlistRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.schemas.event import EventCreate, EventUpdate
from app.utils.email_service import EmailService


class OrganizerService:
    
    def __init__(self, db: Session):
        self.db = db
        self.event_repo = EventRepository(db)
        self.registration_repo = RegistrationRepository(db)
        self.waitlist_repo = WaitlistRepository(db)
        self.category_repo = CategoryRepository(db)
        self.audit_repo = AuditLogRepository(db)
        self.user_repo = UserRepository(db)
        self.email_service = EmailService(db)
    
    def _verify_organizer(self, user: User) -> None:
        if user.role == UserRole.ADMIN:
            return
        
        if user.role != UserRole.ORGANIZER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organizer role required"
            )
        
        if not user.is_approved:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your organizer account is pending approval"
            )
    
    def _verify_event_ownership(self, event: Event, user: User) -> None:
        if user.role == UserRole.ADMIN:
            return
        
        if event.organizer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage this event"
            )
    
    def create_event(
        self,
        event_data: EventCreate,
        organizer: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Event:
        self._verify_organizer(organizer)
        
        category = self.category_repo.get_by_id(event_data.categoryId)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with ID '{event_data.categoryId}' not found"
            )
        
        if not category.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create event with inactive category"
            )
        
        try:
            event_date = date.fromisoformat(event_data.date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
<<<<<<< Updated upstream

        # Check for venue conflicts
        conflicting_event = self.event_repo.check_venue_conflict(
            venue=event_data.venue,
            event_date=event_date,
            start_time=event_data.startTime,
            end_time=event_data.endTime
        )

        if conflicting_event:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Venue '{event_data.venue}' is already booked on {event_data.date} from {conflicting_event.start_time.strftime('%H:%M')} to {conflicting_event.end_time.strftime('%H:%M')} for event '{conflicting_event.title}'"
            )

        # Create event
=======
        
>>>>>>> Stashed changes
        try:
            event = self.event_repo.create(
                title=event_data.title,
                description=event_data.description,
                category_id=event_data.categoryId,
                organizer_id=organizer.id,
                event_date=event_date,
                start_time=event_data.startTime,
                end_time=event_data.endTime,
                venue=event_data.venue,
                location=event_data.location,
                capacity=event_data.capacity,
                image_url=event_data.imageUrl,
                tags=event_data.tags,
                status=EventStatus.PENDING  # Events start as pending for admin approval
            )
            
            self.audit_repo.create(
                action=AuditAction.EVENT_CREATED,
                actor_id=organizer.id,
                actor_name=organizer.name,
                actor_role=organizer.role.value,
                target_type=TargetType.EVENT,
                target_id=event.id,
                target_name=event.title,
                details=f"Event '{event.title}' created by {organizer.name}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return event
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create event: {str(e)}"
            )
    
    def get_organizer_events(
        self,
        organizer: User,
        status_filter: Optional[EventStatus] = None
    ) -> Tuple[List[Event], Dict[str, int]]:
        self._verify_organizer(organizer)
        
        events = self.event_repo.get_by_organizer(organizer.id, status=status_filter)
        statistics = self.event_repo.get_organizer_statistics(organizer.id)
        
        return events, statistics
    
    def update_event(
        self,
        event_id: str,
        event_data: EventUpdate,
        organizer: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Event:
<<<<<<< Updated upstream
        """
        Update an event with complete event data.

        Args:
            event_id: Event ID to update
            event_data: Complete event data (same as create)
            organizer: Current user
            ip_address: Request IP address
            user_agent: Request user agent

        Returns:
            Event: Updated event

        Raises:
            HTTPException: If event not found or validation fails
        """
        self._verify_organizer(organizer)

        # Get event
=======
        self._verify_organizer(organizer)
        
>>>>>>> Stashed changes
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        self._verify_event_ownership(event, organizer)
<<<<<<< Updated upstream

        # Cannot update cancelled events
=======
        
>>>>>>> Stashed changes
        if event.status == EventStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update a cancelled event"
            )
<<<<<<< Updated upstream

        # Validate category exists
        category = self.category_repo.get_by_id(event_data.categoryId)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with ID '{event_data.categoryId}' not found"
            )

        # Validate date
        try:
            event_date = date.fromisoformat(event_data.date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

        # Check for venue conflicts (exclude current event)
        conflicting_event = self.event_repo.check_venue_conflict(
            venue=event_data.venue,
            event_date=event_date,
            start_time=event_data.startTime,
            end_time=event_data.endTime,
            exclude_event_id=event_id
        )

        if conflicting_event:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Venue '{event_data.venue}' is already booked on {event_data.date} from {conflicting_event.start_time.strftime('%H:%M')} to {conflicting_event.end_time.strftime('%H:%M')} for event '{conflicting_event.title}'"
            )

        # Cannot reduce capacity below registered count
        if event_data.capacity < event.registered_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reduce capacity below current registered count ({event.registered_count})"
            )

        # Build update dict with all fields
        update_fields = {
            'title': event_data.title,
            'description': event_data.description,
            'category_id': event_data.categoryId,
            'date': event_date,
            'start_time': event_data.startTime,
            'end_time': event_data.endTime,
            'venue': event_data.venue,
            'location': event_data.location,
            'capacity': event_data.capacity,
            'image_url': event_data.imageUrl,
            'tags': event_data.tags if event_data.tags else []
        }

        # Handle status update if provided
        if event_data.status is not None:
=======
        
        update_fields = {}
        
        if event_data.title is not None:
            update_fields['title'] = event_data.title
        
        if event_data.description is not None:
            update_fields['description'] = event_data.description
        
        if event_data.categoryId is not None:
            category = self.category_repo.get_by_id(event_data.categoryId)
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Category with ID '{event_data.categoryId}' not found"
                )
            update_fields['category_id'] = event_data.categoryId
        
        if event_data.date is not None:
>>>>>>> Stashed changes
            try:
                # Validate and convert status string to EventStatus enum
                new_status = EventStatus(event_data.status.lower())

                # Business rule: Organizers can only set status to 'draft' or 'pending'
                # They cannot directly publish or cancel via update
                if new_status in [EventStatus.DRAFT, EventStatus.PENDING]:
                    update_fields['status'] = new_status
                elif new_status == EventStatus.CANCELLED:
                    # Use the cancel_event method instead
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Use the cancel endpoint to cancel an event"
                    )
                elif new_status == EventStatus.PUBLISHED:
                    # Only admins can publish directly
                    if organizer.role.value != 'admin':
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins can publish events directly. Set status to 'pending' for admin approval."
                        )
                    update_fields['status'] = new_status
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: draft, pending, published, cancelled"
                )
<<<<<<< Updated upstream

        # Update event
        event = self.event_repo.update(event, **update_fields)

        # Log audit
        self.audit_repo.create(
            action=AuditAction.EVENT_UPDATED,
            actor_id=organizer.id,
            actor_name=organizer.name,
            actor_role=organizer.role.value,
            target_type=TargetType.EVENT,
            target_id=event.id,
            target_name=event.title,
            details=f"Event '{event.title}' updated",
            metadata={"updated_fields": list(update_fields.keys())},
            ip_address=ip_address,
            user_agent=user_agent
        )

=======
        
        if event_data.startTime is not None:
            update_fields['start_time'] = event_data.startTime
        
        if event_data.endTime is not None:
            update_fields['end_time'] = event_data.endTime
        
        if event_data.venue is not None:
            update_fields['venue'] = event_data.venue
        
        if event_data.location is not None:
            update_fields['location'] = event_data.location
        
        if event_data.capacity is not None:
            if event_data.capacity < event.registered_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot reduce capacity below current registered count ({event.registered_count})"
                )
            update_fields['capacity'] = event_data.capacity
        
        if event_data.imageUrl is not None:
            update_fields['image_url'] = event_data.imageUrl
        
        if event_data.tags is not None:
            update_fields['tags'] = event_data.tags
        
        if update_fields:
            event = self.event_repo.update(event, **update_fields)
            
            self.audit_repo.create(
                action=AuditAction.EVENT_UPDATED,
                actor_id=organizer.id,
                actor_name=organizer.name,
                actor_role=organizer.role.value,
                target_type=TargetType.EVENT,
                target_id=event.id,
                target_name=event.title,
                details=f"Event '{event.title}' updated",
                metadata={"updated_fields": list(update_fields.keys())},
                ip_address=ip_address,
                user_agent=user_agent
            )
        
>>>>>>> Stashed changes
        return event
    
    def cancel_event(
        self,
        event_id: str,
        organizer: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Event:
        """
        Cancel an event.
        
        Args:
            event_id: Event ID to cancel
            organizer: Current user
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            Event: Cancelled event
            
        Raises:
            HTTPException: If event not found or already cancelled
        """
        self._verify_organizer(organizer)
        
        # Get event
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        self._verify_event_ownership(event, organizer)
        
        # Cannot cancel already cancelled event
        if event.status == EventStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event is already cancelled"
            )
        
        # Cancel the event
        event = self.event_repo.cancel(event)
        
        # Log audit
        self.audit_repo.create(
            action=AuditAction.EVENT_CANCELLED,
            actor_id=organizer.id,
            actor_name=organizer.name,
            actor_role=organizer.role.value,
            target_type=TargetType.EVENT,
            target_id=event.id,
            target_name=event.title,
            details=f"Event '{event.title}' cancelled by {organizer.name}",
            metadata={
                "registered_count": event.registered_count,
                "waitlist_count": event.waitlist_count
            },
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Send cancellation notifications to all registered attendees
        try:
            # Get all confirmed registrations for this event
            registrations = self.registration_repo.get_event_registrations(
                event_id=event.id,
                status=RegistrationStatus.CONFIRMED
            )

            # Send email to each attendee
            for registration in registrations:
                user = self.user_repo.get_by_id(registration.user_id)
                if user:
                    try:
                        self.email_service.send_event_cancellation_to_attendees(
                            attendee=user,
                            event=event
                        )
                    except Exception as email_error:
                        # Log but don't fail the cancellation
                        logger.warning(f"Failed to send cancellation email to {user.email}: {str(email_error)}")

            logger.info(f"Sent cancellation notifications to {len(registrations)} attendees for event {event.id}")
        except Exception as e:
            # Log error but don't fail the cancellation
            logger.error(f"Error sending cancellation notifications: {str(e)}")

        return event
    
    def duplicate_event(
        self,
        event_id: str,
        organizer: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Event:
        """
        Duplicate an event.
        
        Args:
            event_id: Event ID to duplicate
            organizer: Current user
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            Event: New duplicated event
            
        Raises:
            HTTPException: If event not found
        """
        self._verify_organizer(organizer)
        
        # Get original event
        original = self.event_repo.get_by_id(event_id)
        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        self._verify_event_ownership(original, organizer)
        
        # Create duplicate with modified title
        new_title = f"{original.title} (Copy)"
        
        # Create new event
        new_event = self.event_repo.create(
            title=new_title,
            description=original.description,
            category_id=original.category_id,
            organizer_id=organizer.id,
            event_date=original.date,
            start_time=original.start_time.strftime("%H:%M") if original.start_time else "09:00",
            end_time=original.end_time.strftime("%H:%M") if original.end_time else "17:00",
            venue=original.venue,
            location=original.location,
            capacity=original.capacity,
            image_url=original.image_url,
            tags=original.tags if original.tags else [],
            status=EventStatus.DRAFT  # Duplicates start as draft
        )
        
        # Log audit
        self.audit_repo.create(
            action=AuditAction.EVENT_DUPLICATED,
            actor_id=organizer.id,
            actor_name=organizer.name,
            actor_role=organizer.role.value,
            target_type=TargetType.EVENT,
            target_id=new_event.id,
            target_name=new_event.title,
            details=f"Event duplicated from '{original.title}'",
            metadata={"original_event_id": original.id},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return new_event
    
    def get_organizer_statistics(self, organizer: User) -> Dict[str, Any]:
        """
        Get comprehensive statistics for an organizer.
        
        Args:
            organizer: Organizer user
            
        Returns:
            Dict: Statistics dictionary
        """
        self._verify_organizer(organizer)
        
        stats = self.event_repo.get_organizer_statistics(organizer.id)
        
        return {
            "totalEvents": stats.get("total", 0),
            "upcomingEvents": stats.get("upcoming", 0),
            "totalRegistrations": stats.get("total_registrations", 0),
            "eventsByStatus": stats.get("by_status", {}),
            "draftEvents": stats.get("by_status", {}).get("draft", 0),
            "pendingEvents": stats.get("by_status", {}).get("pending", 0),
            "publishedEvents": stats.get("by_status", {}).get("published", 0),
            "cancelledEvents": stats.get("by_status", {}).get("cancelled", 0)
        }
    
    def get_event_attendees(
        self,
        event_id: str,
        organizer: User,
        check_in_filter: Optional[str] = None
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Get attendees for an event.
        
        Args:
            event_id: Event ID
            organizer: Current user
            check_in_filter: Filter by check-in status ('checked_in', 'not_checked_in')
            
        Returns:
            Tuple[List[Dict], Dict]: List of attendees and statistics
            
        Raises:
            HTTPException: If event not found
        """
        self._verify_organizer(organizer)
        
        # Get event
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        self._verify_event_ownership(event, organizer)
        
        # Get registrations
        check_in_status = None
        if check_in_filter:
            if check_in_filter == "checked_in":
                check_in_status = CheckInStatus.CHECKED_IN
            elif check_in_filter == "not_checked_in":
                check_in_status = CheckInStatus.NOT_CHECKED_IN
        
        registrations = self.registration_repo.get_event_registrations(
            event_id=event_id,
            status=RegistrationStatus.CONFIRMED,
            check_in_status=check_in_status
        )
        
        # Build attendee list
        attendees = []
        checked_in_count = 0
        total_attendees = 0  # Including guests
        
        for reg in registrations:
            if reg.check_in_status == CheckInStatus.CHECKED_IN:
                checked_in_count += 1
            
            guest_count = len(reg.guests) if reg.guests else 0
            total_attendees += 1 + guest_count
            
            attendees.append({
                "id": reg.user.id if reg.user else None,
                "registrationId": reg.id,
                "name": reg.user.name if reg.user else "Unknown",
                "email": reg.user.email if reg.user else "Unknown",
                "registeredAt": reg.registered_at.isoformat() if reg.registered_at else None,
                "checkInStatus": reg.check_in_status.value,
                "checkedInAt": reg.checked_in_at.isoformat() if reg.checked_in_at else None,
                "guests": reg.guests if reg.guests else []
            })
        
        # Calculate statistics
        statistics = {
            "totalRegistrations": len(registrations),
            "checkedIn": checked_in_count,
            "notCheckedIn": len(registrations) - checked_in_count,
            "totalAttendees": total_attendees,
            "capacityUsed": f"{(event.registered_count / event.capacity * 100):.1f}%" if event.capacity > 0 else "0%"
        }
        
        return attendees, statistics
    
    def export_attendees_csv(
        self,
        event_id: str,
        organizer: User
    ) -> str:
        """
        Export attendees as CSV.
        
        Args:
            event_id: Event ID
            organizer: Current user
            
        Returns:
            str: CSV content
            
        Raises:
            HTTPException: If event not found
        """
        self._verify_organizer(organizer)
        
        # Get event
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        self._verify_event_ownership(event, organizer)
        
        # Get registrations
        registrations = self.registration_repo.get_event_registrations(
            event_id=event_id,
            status=RegistrationStatus.CONFIRMED
        )
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Name",
            "Email",
            "Registration Date",
            "Ticket Code",
            "Check-in Status",
            "Checked-in At",
            "Guest Count",
            "Guest Names"
        ])
        
        # Data rows
        for reg in registrations:
            guest_names = ", ".join([g.get("name", "") for g in (reg.guests or [])])
            writer.writerow([
                reg.user.name if reg.user else "Unknown",
                reg.user.email if reg.user else "Unknown",
                reg.registered_at.isoformat() if reg.registered_at else "",
                reg.ticket_code,
                reg.check_in_status.value,
                reg.checked_in_at.isoformat() if reg.checked_in_at else "",
                len(reg.guests) if reg.guests else 0,
                guest_names
            ])
        
        return output.getvalue()
    
    def check_in_attendee(
        self,
        event_id: str,
        registration_id: str,
        organizer: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Registration:
        self._verify_organizer(organizer)
        
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        self._verify_event_ownership(event, organizer)
        
        registration = self.registration_repo.get_by_id(registration_id)
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found"
            )
        
        if registration.event_id != event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration does not belong to this event"
            )
        
        if registration.status != RegistrationStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot check-in a cancelled registration"
            )
        
        if registration.check_in_status == CheckInStatus.CHECKED_IN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attendee is already checked in"
            )
        
        registration = self.registration_repo.check_in(registration)
        
        self.audit_repo.create(
            action=AuditAction.ATTENDEE_CHECKED_IN,
            actor_id=organizer.id,
            actor_name=organizer.name,
            actor_role=organizer.role.value,
            target_type=TargetType.REGISTRATION,
            target_id=registration.id,
            target_name=registration.user.name if registration.user else "Unknown",
            details=f"Attendee checked in for '{event.title}'",
            metadata={
                "event_id": event_id,
                "ticket_code": registration.ticket_code
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return registration
    
    def send_announcement(
        self,
        event_id: str,
        subject: str,
        message: str,
        organizer: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:            
        self._verify_organizer(organizer)
        
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        self._verify_event_ownership(event, organizer)
        
        registrations = self.registration_repo.get_event_registrations(
            event_id=event_id,
            status=RegistrationStatus.CONFIRMED
        )
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_announcements = self.audit_repo.count_by_action_and_actor(
            action=AuditAction.EVENT_UPDATED,
            actor_id=organizer.id,
            since=today_start
        )

        if today_announcements >= 10:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily announcement limit reached (10 per day). Please try again tomorrow."
            )

        recipient_count = len(registrations)
        for reg in registrations:
            if reg.guests:
                recipient_count += len([g for g in reg.guests if g.get("email")])

        sent_count = 0
        failed_count = 0

        for registration in registrations:
            user = self.user_repo.get_by_id(registration.user_id)
            if user:
                try:
                    self.email_service.send_announcement(
                        attendee=user,
                        event=event,
                        subject_text=subject,
                        message=message,
                        registration=registration
                    )
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send announcement to {user.email}: {str(e)}")
                    failed_count += 1

        logger.info(f"Sent announcement to {sent_count}/{recipient_count} attendees for event {event.id}")

        self.audit_repo.create(
            action=AuditAction.EVENT_UPDATED,
            actor_id=organizer.id,
            actor_name=organizer.name,
            actor_role=organizer.role.value,
            target_type=TargetType.EVENT,
            target_id=event.id,
            target_name=event.title,
            details=f"Announcement sent for '{event.title}': {subject}",
            metadata={
                "subject": subject,
                "recipient_count": recipient_count,
                "type": "announcement"
            },
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "success": True,
            "message": f"Announcement sent to {sent_count} of {recipient_count} recipients",
            "recipientCount": sent_count,
            "failedCount": failed_count
        }
    
    def get_event_waitlist(
        self,
        event_id: str,
        organizer: User
    ) -> List[Dict]:
        self._verify_organizer(organizer)
        
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        self._verify_event_ownership(event, organizer)
        
        waitlist = self.waitlist_repo.get_event_waitlist(event_id)
        
        waitlist_entries = []
        for entry in waitlist:
            waitlist_entries.append({
                "id": entry.id,
                "userId": entry.user_id,
                "position": entry.position,
                "name": entry.user.name if entry.user else "Unknown",
                "email": entry.user.email if entry.user else "Unknown",
                "joinedAt": entry.joined_at.isoformat() if entry.joined_at else None,
                "notificationPreference": entry.notification_preference.value
            })
        
        return waitlist_entries


