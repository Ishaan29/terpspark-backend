from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OrganizerApprovalRequest(Base):
    __tablename__ = "organizer_approval_requests"
    
    id = Column(String(36), primary_key=True, index=True)
    
    
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    
    reason = Column(
        Text,
        nullable=False,
        comment="Reason why user wants to be an organizer"
    )
    
    
    status = Column(
        SQLEnum(ApprovalStatus),
        nullable=False,
        default=ApprovalStatus.PENDING,
        index=True
    )
    
    
    reviewed_by = Column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
        comment="Admin user ID who reviewed the request"
    )
    notes = Column(Text, nullable=True, comment="Admin notes or feedback")
    
    
    requested_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    
    user = relationship("User", foreign_keys=[user_id], backref="approval_requests")
    reviewer = relationship("User", foreign_keys=[reviewed_by], backref="reviewed_approvals")
    
    def __repr__(self) -> str:
        return f"<OrganizerApprovalRequest(id={self.id}, user_id={self.user_id}, status={self.status})>"
    
    def to_dict(self, include_user: bool = True, include_reviewer: bool = True) -> dict:
        """
        Convert approval request to dictionary.
        
        Args:
            include_user: Whether to include user details
            include_reviewer: Whether to include reviewer details
            
        Returns:
            dict: Approval request data as dictionary
        """
        request_dict = {
            "id": self.id,
            "userId": self.user_id,
            "reason": self.reason,
            "status": self.status.value,
            "reviewedBy": self.reviewed_by,
            "notes": self.notes,
            "requestedAt": self.requested_at.isoformat() if self.requested_at else None,
            "reviewedAt": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
        
        if include_user and self.user:
            request_dict["name"] = self.user.name
            request_dict["email"] = self.user.email
            request_dict["department"] = self.user.department
        
        if include_reviewer and self.reviewer:
            request_dict["reviewer"] = {
                "id": self.reviewer.id,
                "name": self.reviewer.name,
                "email": self.reviewer.email
            }
        
        return request_dict

