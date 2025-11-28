"""
Organizer service for business logic.
Handles event management, attendee management, and communication for organizers.
Phase 4: Organizer Management
"""
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import date, datetime
import uuid
import csv
import io

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
from app.schemas.event import EventCreate, EventUpdate


class OrganizerService:
    """Service for organizer operations."""
    
    def __init__(self, db: Session):
        """
        Initialize service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.event_repo = EventRepository(db)
        self.registration_repo = RegistrationRepository(db)
        self.waitlist_repo = WaitlistRepository(db)
        self.category_repo = CategoryRepository(db)
        self.audit_repo = AuditLogRepository(db)
    
    def _verify_organizer(self, user: User) -> None:
        """
        Verify that user is an approved organizer or admin.
        
        Args:
            user: Current user
            
        Raises:
            HTTPException: If user is not an approved organizer
        """
        if user.role == UserRole.ADMIN:
            return  # Admins can do anything
        
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
        """
        Verify that user owns the event or is admin.
        
        Args:
            event: Event to check
            user: Current user
            
        Raises:
            HTTPException: If user doesn't own the event
        """
        if user.role == UserRole.ADMIN:
            return  # Admins can manage any event
        
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
        """
        Create a new event.
        
        Args:
            event_data: Event creation data
            organizer: Organizer creating the event
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            Event: Created event
            
        Raises:
            HTTPException: If validation fails
        """
        self._verify_organizer(organizer)
        
        # Validate category exists
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
        
        # Parse date
        try:
            event_date = date.fromisoformat(event_data.date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        # Create event
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
            
            # Log audit
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
        """
        Get all events for an organizer.
        
        Args:
            organizer: Organizer user
            status_filter: Filter by event status
            
        Returns:
            Tuple[List[Event], Dict]: List of events and statistics
        """
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
        """
        Update an event.
        
        Args:
            event_id: Event ID to update
            event_data: Update data
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
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        self._verify_event_ownership(event, organizer)
        
        # Cannot update cancelled events
        if event.status == EventStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update a cancelled event"
            )
        
        # Build update dict
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
            try:
                update_fields['date'] = date.fromisoformat(event_data.date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        
        if event_data.startTime is not None:
            update_fields['start_time'] = event_data.startTime
        
        if event_data.endTime is not None:
            update_fields['end_time'] = event_data.endTime
        
        if event_data.venue is not None:
            update_fields['venue'] = event_data.venue
        
        if event_data.location is not None:
            update_fields['location'] = event_data.location
        
        if event_data.capacity is not None:
            # Cannot reduce capacity below registered count
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
        
        # Update event
        if update_fields:
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
        
        # TODO: Send cancellation notifications to registered users
        
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
        """
        Check-in an attendee.
        
        Args:
            event_id: Event ID
            registration_id: Registration ID
            organizer: Current user
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            Registration: Updated registration
            
        Raises:
            HTTPException: If registration not found or invalid
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
        
        # Get registration
        registration = self.registration_repo.get_by_id(registration_id)
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found"
            )
        
        # Verify registration is for this event
        if registration.event_id != event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration does not belong to this event"
            )
        
        # Verify registration is confirmed
        if registration.status != RegistrationStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot check-in a cancelled registration"
            )
        
        # Check if already checked in
        if registration.check_in_status == CheckInStatus.CHECKED_IN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attendee is already checked in"
            )
        
        # Check in
        registration = self.registration_repo.check_in(registration)
        
        # Log audit
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
        """
        Send announcement to all registered attendees.
        
        Args:
            event_id: Event ID
            subject: Announcement subject
            message: Announcement message
            organizer: Current user
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            Dict: Result with recipient count
            
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
        
        # Count recipients (including guests with emails)
        recipient_count = len(registrations)
        for reg in registrations:
            if reg.guests:
                recipient_count += len([g for g in reg.guests if g.get("email")])
        
        # TODO: Actually send emails via email service
        # For now, we just log and return count
        
        # Log audit
        self.audit_repo.create(
            action=AuditAction.EVENT_UPDATED,  # Using EVENT_UPDATED for announcements
            actor_id=organizer.id,
            actor_name=organizer.name,
            actor_role=organizer.role.value,
            target_type=TargetType.EVENT,
            target_id=event.id,
            target_name=event.title,
            details=f"Announcement sent for '{event.title}': {subject}",
            metadata={
                "subject": subject,
                "recipient_count": recipient_count
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return {
            "success": True,
            "message": f"Announcement queued for {recipient_count} recipients",
            "recipientCount": recipient_count
        }
    
    def get_event_waitlist(
        self,
        event_id: str,
        organizer: User
    ) -> List[Dict]:
        """
        Get waitlist for an event.
        
        Args:
            event_id: Event ID
            organizer: Current user
            
        Returns:
            List[Dict]: List of waitlist entries
            
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
        
        # Get waitlist
        waitlist = self.waitlist_repo.get_event_waitlist(event_id)
        
        # Build response
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


