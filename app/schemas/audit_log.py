from pydantic import BaseModel
from typing import Optional


class ActorInfo(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None


class TargetInfo(BaseModel):
    type: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: str
    timestamp: str
    action: str
    actor: Optional[ActorInfo] = None
    target: Optional[TargetInfo] = None
    details: Optional[str] = None
    metadata: Optional[dict] = {}
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None
    
    class Config:
        from_attributes = True


class PaginationInfo(BaseModel):
    currentPage: int
    totalPages: int
    totalItems: int


class AuditLogsListResponse(BaseModel):
    success: bool = True
    logs: list[AuditLogResponse]
    pagination: PaginationInfo

