from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from app.models.registration import Registration, RegistrationStatus, CheckInStatus
import uuid


class RegistrationRepository:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, registration_id: str, include_relations: bool = True) -> Optional[Registration]:
        query = self.db.query(Registration).filter(Registration.id == registration_id)
        if include_relations:
            query = query.options(
                joinedload(Registration.user),
                joinedload(Registration.event)
            )
        return query.first()
    
    def get_by_user_and_event(
        self,
        user_id: str,
        event_id: str
    ) -> Optional[Registration]:
        return self.db.query(Registration).filter(
            Registration.user_id == user_id,
            Registration.event_id == event_id,
            Registration.status == RegistrationStatus.CONFIRMED
        ).first()
    
    def get_user_registrations(
        self,
        user_id: str,
        status: Optional[RegistrationStatus] = None,
        include_past: bool = False
    ) -> List[Registration]:
        from app.models.event import Event
        from datetime import date
        
        query = self.db.query(Registration).join(Event).filter(
            Registration.user_id == user_id
        )
        
        if status:
            query = query.filter(Registration.status == status)
        
        if not include_past:
            query = query.filter(Event.date >= date.today())
        
        return query.options(
            joinedload(Registration.event).joinedload(Event.organizer)
        ).order_by(Event.date, Event.start_time).all()
    
    def get_event_registrations(
        self,
        event_id: str,
        status: Optional[RegistrationStatus] = None,
        check_in_status: Optional[CheckInStatus] = None
    ) -> List[Registration]:
        query = self.db.query(Registration).filter(
            Registration.event_id == event_id
        )
        
        if status:
            query = query.filter(Registration.status == status)
        
        if check_in_status:
            query = query.filter(Registration.check_in_status == check_in_status)
        
        return query.options(joinedload(Registration.user)).order_by(
            Registration.registered_at
        ).all()
    
    def create(
        self,
        user_id: str,
        event_id: str,
        ticket_code: str,
        qr_code: Optional[str] = None,
        guests: Optional[List[dict]] = None,
        sessions: Optional[List[str]] = None
    ) -> Registration:
        registration_id = str(uuid.uuid4())
        
        registration = Registration(
            id=registration_id,
            user_id=user_id,
            event_id=event_id,
            status=RegistrationStatus.CONFIRMED,
            ticket_code=ticket_code,
            qr_code=qr_code,
            check_in_status=CheckInStatus.NOT_CHECKED_IN,
            guests=guests if guests else [],
            sessions=sessions if sessions else [],
            reminder_sent=False
        )
        
        try:
            self.db.add(registration)
            self.db.commit()
            self.db.refresh(registration)
            return registration
        except IntegrityError:
            self.db.rollback()
            raise
    
    def cancel(self, registration: Registration) -> Registration:
        registration.status = RegistrationStatus.CANCELLED
        registration.cancelled_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(registration)
        return registration
    
    def check_in(self, registration: Registration) -> Registration:
        registration.check_in_status = CheckInStatus.CHECKED_IN
        registration.checked_in_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(registration)
        return registration
    
    def mark_reminder_sent(self, registration: Registration) -> Registration:
        registration.reminder_sent = True
        self.db.commit()
        self.db.refresh(registration)
        return registration
    
    def count_event_registrations(
        self,
        event_id: str,
        status: RegistrationStatus = RegistrationStatus.CONFIRMED
    ) -> int:
        return self.db.query(Registration).filter(
            Registration.event_id == event_id,
            Registration.status == status
        ).count()
    
    def get_registrations_needing_reminder(self, event_date) -> List[Registration]:
        from app.models.event import Event
        
        return self.db.query(Registration).join(Event).filter(
            Event.date == event_date,
            Registration.status == RegistrationStatus.CONFIRMED,
            Registration.reminder_sent == False
        ).all()

