from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import date, datetime
from sqlalchemy import func, and_

from app.models.user import User, UserRole
from app.models.event import Event, EventStatus
from app.models.organizer_approval import OrganizerApprovalRequest, ApprovalStatus
from app.models.category import Category
from app.models.venue import Venue
from app.models.audit_log import AuditLog, AuditAction, TargetType
from app.models.registration import Registration, CheckInStatus, RegistrationStatus
from app.repositories.user_repository import UserRepository
from app.repositories.event_repository import EventRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.venue_repository import VenueRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.registration_repository import RegistrationRepository
from app.utils.email_service import EmailService


class AdminService:

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.event_repo = EventRepository(db)
        self.category_repo = CategoryRepository(db)
        self.venue_repo = VenueRepository(db)
        self.audit_repo = AuditLogRepository(db)
        self.registration_repo = RegistrationRepository(db)
        self.email_service = EmailService(db)

    def _verify_admin(self, user: User) -> None:
        if user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required"
            )


    def get_organizer_approvals(
        self,
        admin: User,
        status_filter: str = "pending"
    ) -> List[OrganizerApprovalRequest]:
        self._verify_admin(admin)

        query = self.db.query(OrganizerApprovalRequest).join(
            User, OrganizerApprovalRequest.user_id == User.id
        )

        if status_filter != "all":
            status_map = {
                "pending": ApprovalStatus.PENDING,
                "approved": ApprovalStatus.APPROVED,
                "rejected": ApprovalStatus.REJECTED
            }
            if status_filter in status_map:
                query = query.filter(OrganizerApprovalRequest.status == status_map[status_filter])

        return query.order_by(OrganizerApprovalRequest.requested_at.desc()).all()

    def approve_organizer(
        self,
        request_id: str,
        admin: User,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> OrganizerApprovalRequest:
        self._verify_admin(admin)

        approval_request = self.db.query(OrganizerApprovalRequest).filter(
            OrganizerApprovalRequest.id == request_id
        ).first()

        if not approval_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organizer request not found"
            )

        if approval_request.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Request already {approval_request.status.value}"
            )

        user = self.user_repo.get_by_id(approval_request.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user.role = UserRole.ORGANIZER
        user.is_approved = True

        approval_request.status = ApprovalStatus.APPROVED
        approval_request.reviewed_by = admin.id
        approval_request.reviewed_at = datetime.now()
        approval_request.notes = notes

        try:
            self.email_service.send_organizer_approval(user=user, notes=notes)
        except Exception as e:
            print(f"Warning: Failed to send approval email: {str(e)}")

        self.audit_repo.create(
            action=AuditAction.ORGANIZER_APPROVED,
            actor_id=admin.id,
            actor_name=admin.name,
            actor_role=admin.role.value,
            target_type=TargetType.USER,
            target_id=user.id,
            target_name=user.name,
            details=f"Admin {admin.name} approved organizer request from {user.name}",
            metadata={"notes": notes} if notes else None,
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.db.commit()
        self.db.refresh(approval_request)

        return approval_request

    def reject_organizer(
        self,
        request_id: str,
        admin: User,
        notes: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> OrganizerApprovalRequest:
        self._verify_admin(admin)

        approval_request = self.db.query(OrganizerApprovalRequest).filter(
            OrganizerApprovalRequest.id == request_id
        ).first()

        if not approval_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organizer request not found"
            )

        if approval_request.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Request already {approval_request.status.value}"
            )

        user = self.user_repo.get_by_id(approval_request.user_id)

        approval_request.status = ApprovalStatus.REJECTED
        approval_request.reviewed_by = admin.id
        approval_request.reviewed_at = datetime.now()
        approval_request.notes = notes

        try:
            self.email_service.send_organizer_rejection(user=user, notes=notes)
        except Exception as e:
            print(f"Warning: Failed to send rejection email: {str(e)}")

        self.audit_repo.create(
            action=AuditAction.ORGANIZER_REJECTED,
            actor_id=admin.id,
            actor_name=admin.name,
            actor_role=admin.role.value,
            target_type=TargetType.USER,
            target_id=user.id if user else approval_request.user_id,
            target_name=user.name if user else "Unknown User",
            details=f"Admin {admin.name} rejected organizer request from {user.name if user else 'user'}",
            metadata={"reason": notes},
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.db.commit()
        self.db.refresh(approval_request)

        return approval_request

    def get_pending_events(self, admin: User) -> List[Event]:
        self._verify_admin(admin)

        return self.event_repo.get_pending_events()

    def approve_event(
        self,
        event_id: str,
        admin: User,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Event:
        self._verify_admin(admin)

        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        if event.status != EventStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event is not pending (current status: {event.status.value})"
            )

        event.status = EventStatus.PUBLISHED
        event.published_at = datetime.now()

        organizer = event.organizer
        try:
            self.email_service.send_event_approval(organizer=organizer, event=event, notes=notes)
        except Exception as e:
            print(f"Warning: Failed to send approval email: {str(e)}")

        self.audit_repo.create(
            action=AuditAction.EVENT_APPROVED,
            actor_id=admin.id,
            actor_name=admin.name,
            actor_role=admin.role.value,
            target_type=TargetType.EVENT,
            target_id=event.id,
            target_name=event.title,
            details=f"Admin {admin.name} approved and published event '{event.title}'",
            metadata={"notes": notes} if notes else None,
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.db.commit()
        self.db.refresh(event)

        return event

    def reject_event(
        self,
        event_id: str,
        admin: User,
        notes: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Event:
        self._verify_admin(admin)

        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        if event.status != EventStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event is not pending (current status: {event.status.value})"
            )

        event.status = EventStatus.CANCELLED
        event.cancelled_at = datetime.now()

        organizer = event.organizer
        try:
            self.email_service.send_event_rejection(organizer=organizer, event=event, notes=notes)
        except Exception as e:
            print(f"Warning: Failed to send rejection email: {str(e)}")

        self.audit_repo.create(
            action=AuditAction.EVENT_REJECTED,
            actor_id=admin.id,
            actor_name=admin.name,
            actor_role=admin.role.value,
            target_type=TargetType.EVENT,
            target_id=event.id,
            target_name=event.title,
            details=f"Admin {admin.name} rejected event '{event.title}'",
            metadata={"reason": notes},
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.db.commit()
        self.db.refresh(event)

        return event

    def get_all_categories(self, admin: User, include_inactive: bool = True) -> List[Category]:
        self._verify_admin(admin)
        return self.category_repo.get_all(active_only=not include_inactive)

    def create_category(
        self,
        admin: User,
        name: str,
        color: str,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Category:
        self._verify_admin(admin)

        if not slug:
            slug = name.lower().replace(" ", "-").replace("&", "and")

        existing = self.category_repo.get_by_slug(slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category with slug '{slug}' already exists"
            )

        category = self.category_repo.create(
            name=name,
            slug=slug,
            color=color,
            description=description,
            icon=icon
        )

        self.audit_repo.create(
            action=AuditAction.CATEGORY_CREATED,
            actor_id=admin.id,
            actor_name=admin.name,
            actor_role=admin.role.value,
            target_type=TargetType.CATEGORY,
            target_id=category.id,
            target_name=category.name,
            details=f"Admin {admin.name} created category '{category.name}'",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return category

    def update_category(
        self,
        category_id: str,
        admin: User,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Category:
        self._verify_admin(admin)

        category = self.category_repo.get_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

        updates = {}
        if name is not None:
            updates['name'] = name
        if description is not None:
            updates['description'] = description
        if color is not None:
            updates['color'] = color
        if icon is not None:
            updates['icon'] = icon

        if updates:
            category = self.category_repo.update(category, **updates)

            self.audit_repo.create(
                action=AuditAction.CATEGORY_UPDATED,
                actor_id=admin.id,
                actor_name=admin.name,
                actor_role=admin.role.value,
                target_type=TargetType.CATEGORY,
                target_id=category.id,
                target_name=category.name,
                details=f"Admin {admin.name} updated category '{category.name}'",
                metadata={"updated_fields": list(updates.keys())},
                ip_address=ip_address,
                user_agent=user_agent
            )

        return category

    def toggle_category(
        self,
        category_id: str,
        admin: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Category:
        self._verify_admin(admin)

        category = self.category_repo.get_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

        if category.is_active:
            event_count = self.category_repo.count_events_using_category(category_id)
            if event_count > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot retire category with {event_count} active event(s)"
                )

        category = self.category_repo.toggle_active(category)

        action_text = "retired" if not category.is_active else "reactivated"

        self.audit_repo.create(
            action=AuditAction.CATEGORY_RETIRED,
            actor_id=admin.id,
            actor_name=admin.name,
            actor_role=admin.role.value,
            target_type=TargetType.CATEGORY,
            target_id=category.id,
            target_name=category.name,
            details=f"Admin {admin.name} {action_text} category '{category.name}'",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return category

    def get_all_venues(self, admin: User, include_inactive: bool = True) -> List[Venue]:
        self._verify_admin(admin)
        return self.venue_repo.get_all(active_only=not include_inactive)

    def create_venue(
        self,
        admin: User,
        name: str,
        building: str,
        capacity: Optional[int] = None,
        facilities: Optional[List[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Venue:
        self._verify_admin(admin)

        venue = self.venue_repo.create(
            name=name,
            building=building,
            capacity=capacity,
            facilities=facilities
        )

        self.audit_repo.create(
            action=AuditAction.VENUE_CREATED,
            actor_id=admin.id,
            actor_name=admin.name,
            actor_role=admin.role.value,
            target_type=TargetType.VENUE,
            target_id=venue.id,
            target_name=venue.name,
            details=f"Admin {admin.name} created venue '{venue.name}' in {venue.building}",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return venue

    def update_venue(
        self,
        venue_id: str,
        admin: User,
        name: Optional[str] = None,
        building: Optional[str] = None,
        capacity: Optional[int] = None,
        facilities: Optional[List[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Venue:
        self._verify_admin(admin)

        venue = self.venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )

        updates = {}
        if name is not None:
            updates['name'] = name
        if building is not None:
            updates['building'] = building
        if capacity is not None:
            updates['capacity'] = capacity
        if facilities is not None:
            updates['facilities'] = facilities

        if updates:
            venue = self.venue_repo.update(venue, **updates)

            self.audit_repo.create(
                action=AuditAction.VENUE_UPDATED,
                actor_id=admin.id,
                actor_name=admin.name,
                actor_role=admin.role.value,
                target_type=TargetType.VENUE,
                target_id=venue.id,
                target_name=venue.name,
                details=f"Admin {admin.name} updated venue '{venue.name}'",
                metadata={"updated_fields": list(updates.keys())},
                ip_address=ip_address,
                user_agent=user_agent
            )

        return venue

    def toggle_venue(
        self,
        venue_id: str,
        admin: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Venue:
        self._verify_admin(admin)

        venue = self.venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )

        venue = self.venue_repo.toggle_active(venue)

        action_text = "retired" if not venue.is_active else "reactivated"

        self.audit_repo.create(
            action=AuditAction.VENUE_RETIRED,
            actor_id=admin.id,
            actor_name=admin.name,
            actor_role=admin.role.value,
            target_type=TargetType.VENUE,
            target_id=venue.id,
            target_name=venue.name,
            details=f"Admin {admin.name} {action_text} venue '{venue.name}'",
            ip_address=ip_address,
            user_agent=user_agent
        )

        return venue

    def get_audit_logs(
        self,
        admin: User,
        action: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Tuple[List[AuditLog], int]:
        self._verify_admin(admin)

        start_date_obj = date.fromisoformat(start_date) if start_date else None
        end_date_obj = date.fromisoformat(end_date) if end_date else None

        action_enum = None
        if action:
            try:
                action_enum = AuditAction[action]
            except KeyError:
                pass

        return self.audit_repo.get_all(
            action=action_enum,
            start_date=start_date_obj,
            end_date=end_date_obj,
            actor_id=user_id,
            search=search,
            page=page,
            limit=limit
        )

    def get_analytics(
        self,
        admin: User,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        self._verify_admin(admin)

        # TODO: Implement comprehensive analytics queries

        total_events = self.db.query(Event).count()
        total_registrations = self.db.query(Registration).filter(
            Registration.status == RegistrationStatus.CONFIRMED
        ).count()
        total_attendance = self.db.query(Registration).filter(
            Registration.check_in_status == CheckInStatus.CHECKED_IN
        ).count()
        no_shows = total_registrations - total_attendance
        attendance_rate = (total_attendance / total_registrations * 100) if total_registrations > 0 else 0

        active_organizers = self.db.query(User).filter(
            User.role == UserRole.ORGANIZER,
            User.is_approved == True,
            User.is_active == True
        ).count()

        active_students = self.db.query(User).filter(
            User.role == UserRole.STUDENT,
            User.is_active == True
        ).count()

        
        from sqlalchemy import func
        category_analytics = []
        categories = self.category_repo.get_all(active_only=True)
        for cat in categories:
            cat_events = self.db.query(Event).filter(Event.category_id == cat.id).all()
            cat_registrations = sum([e.registered_count for e in cat_events])
            cat_attendance = self.db.query(Registration).join(Event).filter(
                Event.category_id == cat.id,
                Registration.check_in_status == CheckInStatus.CHECKED_IN
            ).count()
            cat_rate = (cat_attendance / cat_registrations * 100) if cat_registrations > 0 else 0

            category_analytics.append({
                "category": cat.name,
                "events": len(cat_events),
                "registrations": cat_registrations,
                "attendance": cat_attendance,
                "attendanceRate": round(cat_rate, 1)
            })

        # Analytics by date (last 30 days)
        from datetime import timedelta
        date_analytics = []
        today = datetime.now().date()
        for i in range(30, -1, -1):
            target_date = today - timedelta(days=i)
            day_events = self.db.query(Event).filter(Event.date == target_date).count()
            day_registrations = self.db.query(Registration).join(Event).filter(
                Event.date == target_date,
                Registration.status == RegistrationStatus.CONFIRMED
            ).count()
            day_attendance = self.db.query(Registration).join(Event).filter(
                Event.date == target_date,
                Registration.check_in_status == CheckInStatus.CHECKED_IN
            ).count()

            if day_events > 0 or day_registrations > 0 or day_attendance > 0:
                date_analytics.append({
                    "date": target_date.isoformat(),
                    "events": day_events,
                    "registrations": day_registrations,
                    "attendance": day_attendance
                })

        
        top_events = []
        events = self.db.query(Event).filter(
            Event.status == EventStatus.PUBLISHED
        ).order_by(Event.registered_count.desc()).limit(10).all()

        for event in events:
            event_attendance = self.db.query(Registration).filter(
                Registration.event_id == event.id,
                Registration.check_in_status == CheckInStatus.CHECKED_IN
            ).count()
            event_rate = (event_attendance / event.registered_count * 100) if event.registered_count > 0 else 0

            top_events.append({
                "id": event.id,
                "title": event.title,
                "registrations": event.registered_count,
                "attendance": event_attendance,
                "attendanceRate": round(event_rate, 1)
            })

        
        organizer_stats = []
        organizers = self.db.query(User).filter(
            User.role == UserRole.ORGANIZER,
            User.is_approved == True,
            User.is_active == True
        ).limit(20).all()

        for organizer in organizers:
            org_events = self.db.query(Event).filter(Event.organizer_id == organizer.id).all()
            org_registrations = sum([e.registered_count for e in org_events])
            org_attendance = self.db.query(Registration).join(Event).filter(
                Event.organizer_id == organizer.id,
                Registration.check_in_status == CheckInStatus.CHECKED_IN
            ).count()
            avg_attendance = (org_attendance / org_registrations * 100) if org_registrations > 0 else 0

            organizer_stats.append({
                "organizerId": organizer.id,
                "name": organizer.name,
                "eventsCreated": len(org_events),
                "totalRegistrations": org_registrations,
                "averageAttendance": round(avg_attendance, 1)
            })

        return {
            "summary": {
                "totalEvents": total_events,
                "totalRegistrations": total_registrations,
                "totalAttendance": total_attendance,
                "noShows": no_shows,
                "attendanceRate": round(attendance_rate, 1),
                "activeOrganizers": active_organizers,
                "activeStudents": active_students
            },
            "byCategory": category_analytics,
            "byDate": date_analytics,
            "topEvents": top_events,
            "organizerStats": organizer_stats
        }

    def get_dashboard_stats(self, admin: User) -> Dict[str, Any]:
        self._verify_admin(admin)

        pending_organizers = self.db.query(OrganizerApprovalRequest).filter(
            OrganizerApprovalRequest.status == ApprovalStatus.PENDING
        ).count()

        pending_events = self.db.query(Event).filter(
            Event.status == EventStatus.PENDING
        ).count()

        total_events = self.db.query(Event).count()
        total_registrations = self.db.query(Registration).filter(
            Registration.status == RegistrationStatus.CONFIRMED
        ).count()
        total_attendance = self.db.query(Registration).filter(
            Registration.check_in_status == CheckInStatus.CHECKED_IN
        ).count()

        active_organizers = self.db.query(User).filter(
            User.role == UserRole.ORGANIZER,
            User.is_approved == True,
            User.is_active == True
        ).count()

        active_students = self.db.query(User).filter(
            User.role == UserRole.STUDENT,
            User.is_active == True
        ).count()

        return {
            "pendingOrganizers": pending_organizers,
            "pendingEvents": pending_events,
            "totalPending": pending_organizers + pending_events,
            "totalEvents": total_events,
            "totalRegistrations": total_registrations,
            "totalAttendance": total_attendance,
            "activeOrganizers": active_organizers,
            "activeStudents": active_students
        }
