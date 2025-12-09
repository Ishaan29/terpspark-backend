from pydantic import BaseModel, Field
from typing import Optional


class OrganizerApprovalCreate(BaseModel):
    reason: str = Field(..., min_length=20, max_length=2000, description="Reason for wanting to become organizer")


class OrganizerApprovalAction(BaseModel):
    notes: Optional[str] = Field(None, max_length=2000)


class OrganizerApprovalReject(BaseModel):
    notes: str = Field(..., min_length=10, max_length=2000, description="Reason for rejection (required)")


class ReviewerInfo(BaseModel):
    id: str
    name: str
    email: str


class OrganizerApprovalResponse(BaseModel):
    id: str
    userId: str
    name: str
    email: str
    department: Optional[str] = None
    reason: str
    status: str
    reviewedBy: Optional[str] = None
    reviewer: Optional[ReviewerInfo] = None
    notes: Optional[str] = None
    requestedAt: str
    reviewedAt: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrganizerApprovalsListResponse(BaseModel):
    success: bool = True
    requests: list[OrganizerApprovalResponse]


class OrganizerApprovalActionResponse(BaseModel):
    success: bool = True
    message: str

