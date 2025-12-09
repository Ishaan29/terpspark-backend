from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class OrganizerApprovalResponse(BaseModel):
    id: str
    userId: str
    name: str
    email: str
    department: Optional[str] = None
    reason: str
    requestedAt: str
    status: str
    reviewedBy: Optional[str] = None
    reviewedAt: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class OrganizerApprovalsResponse(BaseModel):
    success: bool = True
    requests: List[OrganizerApprovalResponse]


class ApprovalActionRequest(BaseModel):
    notes: Optional[str] = None


class RejectionRequest(BaseModel):
    notes: str = Field(..., min_length=10, description="Reason for rejection")


class EventApprovalOrganizerInfo(BaseModel):
    id: str
    name: str
    email: str


class EventApprovalCategoryInfo(BaseModel):
    name: str


class EventApprovalResponse(BaseModel):
    id: str
    title: str
    description: str
    category: EventApprovalCategoryInfo
    organizer: EventApprovalOrganizerInfo
    date: str
    startTime: str
    endTime: str
    venue: str
    capacity: int
    submittedAt: str
    status: str

    class Config:
        from_attributes = True


class EventApprovalsResponse(BaseModel):
    success: bool = True
    events: List[EventApprovalResponse]


class AuditLogActorInfo(BaseModel):
    id: str
    name: str
    role: str


class AuditLogTargetInfo(BaseModel):
    type: str
    id: str
    name: str


class AuditLogResponse(BaseModel):
    id: str
    timestamp: str
    action: str
    actor: AuditLogActorInfo
    target: AuditLogTargetInfo
    details: str
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class PaginationInfo(BaseModel):
    currentPage: int
    totalPages: int
    totalItems: int
    itemsPerPage: int


class AuditLogsResponse(BaseModel):
    success: bool = True
    logs: List[AuditLogResponse]
    pagination: PaginationInfo


class AnalyticsSummary(BaseModel):
    totalEvents: int
    totalRegistrations: int
    totalAttendance: int
    noShows: int
    attendanceRate: float
    activeOrganizers: int
    activeStudents: int


class CategoryAnalytics(BaseModel):
    category: str
    events: int
    registrations: int
    attendance: int
    attendanceRate: float


class DateAnalytics(BaseModel):
    date: str
    events: int
    registrations: int
    attendance: int


class TopEvent(BaseModel):
    id: str
    title: str
    registrations: int
    attendance: int
    attendanceRate: float


class OrganizerStats(BaseModel):
    organizerId: str
    name: str
    eventsCreated: int
    totalRegistrations: int
    averageAttendance: float


class AnalyticsData(BaseModel):
    summary: AnalyticsSummary
    byCategory: List[CategoryAnalytics]
    byDate: List[DateAnalytics]
    topEvents: List[TopEvent]
    organizerStats: List[OrganizerStats]


class AnalyticsResponse(BaseModel):
    success: bool = True
    analytics: AnalyticsData


class DashboardStats(BaseModel):
    pendingOrganizers: int
    pendingEvents: int
    totalPending: int
    totalEvents: int
    totalRegistrations: int
    totalAttendance: int
    activeOrganizers: int
    activeStudents: int


class DashboardResponse(BaseModel):
    success: bool = True
    stats: DashboardStats


class AdminActionResponse(BaseModel):
    success: bool = True
    message: str


class CategoryCreatedResponse(BaseModel):
    success: bool = True
    message: str
    category: Dict[str, Any]


class VenueCreatedResponse(BaseModel):
    success: bool = True
    message: str
    venue: Dict[str, Any]
