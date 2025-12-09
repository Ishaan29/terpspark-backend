from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from app.models.organizer_approval import OrganizerApprovalRequest, ApprovalStatus
import uuid


class OrganizerApprovalRepository:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, request_id: str, include_relations: bool = True) -> Optional[OrganizerApprovalRequest]:
        query = self.db.query(OrganizerApprovalRequest).filter(
            OrganizerApprovalRequest.id == request_id
        )
        if include_relations:
            query = query.options(
                joinedload(OrganizerApprovalRequest.user),
                joinedload(OrganizerApprovalRequest.reviewer)
            )
        return query.first()
    
    def get_by_user(self, user_id: str) -> Optional[OrganizerApprovalRequest]:
        return self.db.query(OrganizerApprovalRequest).filter(
            OrganizerApprovalRequest.user_id == user_id
        ).order_by(OrganizerApprovalRequest.requested_at.desc()).first()
    
    def get_all(self, status: Optional[ApprovalStatus] = None) -> List[OrganizerApprovalRequest]:
        query = self.db.query(OrganizerApprovalRequest)
        
        if status:
            query = query.filter(OrganizerApprovalRequest.status == status)
        
        return query.options(
            joinedload(OrganizerApprovalRequest.user)
        ).order_by(OrganizerApprovalRequest.requested_at).all()
    
    def get_pending(self) -> List[OrganizerApprovalRequest]:
        return self.get_all(status=ApprovalStatus.PENDING)
    
    def create(self, user_id: str, reason: str) -> OrganizerApprovalRequest:
        request_id = str(uuid.uuid4())
        
        request = OrganizerApprovalRequest(
            id=request_id,
            user_id=user_id,
            reason=reason,
            status=ApprovalStatus.PENDING
        )
        
        try:
            self.db.add(request)
            self.db.commit()
            self.db.refresh(request)
            return request
        except IntegrityError:
            self.db.rollback()
            raise
    
    def approve(
        self,
        request: OrganizerApprovalRequest,
        reviewer_id: str,
        notes: Optional[str] = None
    ) -> OrganizerApprovalRequest:
        request.status = ApprovalStatus.APPROVED
        request.reviewed_by = reviewer_id
        request.reviewed_at = datetime.utcnow()
        request.notes = notes
        
        self.db.commit()
        self.db.refresh(request)
        return request
    
    def reject(
        self,
        request: OrganizerApprovalRequest,
        reviewer_id: str,
        notes: str
    ) -> OrganizerApprovalRequest:
        request.status = ApprovalStatus.REJECTED
        request.reviewed_by = reviewer_id
        request.reviewed_at = datetime.utcnow()
        request.notes = notes
        
        self.db.commit()
        self.db.refresh(request)
        return request
    
    def count_pending(self) -> int:
        return self.db.query(OrganizerApprovalRequest).filter(
            OrganizerApprovalRequest.status == ApprovalStatus.PENDING
        ).count()

