"""
Pydantic schemas for admin requests and responses.
Provides data validation and serialization for admin endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# ORGANIZER APPROVAL SCHEMAS
# ============================================================================

class OrganizerApprovalResponse(BaseModel):
    """Schema for organizer approval request in responses."""
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
    """Schema for list of organizer approvals."""
    success: bool = True
    requests: List[OrganizerApprovalResponse]


class ApprovalActionRequest(BaseModel):
    """Schema for approval/rejection action."""
    notes: Optional[str] = None


class RejectionRequest(BaseModel):
    """Schema for rejection action (notes required)."""
    notes: str = Field(..., min_length=10, description="Reason for rejection")


# ============================================================================
# EVENT APPROVAL SCHEMAS
# ============================================================================

class EventApprovalOrganizerInfo(BaseModel):
    """Organizer info in event approval response."""
    id: str
    name: str
    email: str


class EventApprovalCategoryInfo(BaseModel):
    """Category info in event approval response."""
    name: str


class EventApprovalResponse(BaseModel):
    """Schema for event awaiting approval."""
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
    """Schema for list of events awaiting approval."""
    success: bool = True
    events: List[EventApprovalResponse]


# ============================================================================
# AUDIT LOG SCHEMAS
# ============================================================================

class AuditLogActorInfo(BaseModel):
    """Actor information in audit log."""
    id: str
    name: str
    role: str


class AuditLogTargetInfo(BaseModel):
    """Target information in audit log."""
    type: str
    id: str
    name: str


class AuditLogResponse(BaseModel):
    """Schema for audit log entry."""
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
    """Pagination information."""
    currentPage: int
    totalPages: int
    totalItems: int
    itemsPerPage: int


class AuditLogsResponse(BaseModel):
    """Schema for paginated audit logs response."""
    success: bool = True
    logs: List[AuditLogResponse]
    pagination: PaginationInfo


# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class AnalyticsSummary(BaseModel):
    """Summary statistics."""
    totalEvents: int
    totalRegistrations: int
    totalAttendance: int
    noShows: int
    attendanceRate: float
    activeOrganizers: int
    activeStudents: int


class CategoryAnalytics(BaseModel):
    """Analytics by category."""
    category: str
    events: int
    registrations: int
    attendance: int
    attendanceRate: float


class DateAnalytics(BaseModel):
    """Analytics by date."""
    date: str
    events: int
    registrations: int
    attendance: int


class TopEvent(BaseModel):
    """Top performing event."""
    id: str
    title: str
    registrations: int
    attendance: int
    attendanceRate: float


class OrganizerStats(BaseModel):
    """Organizer statistics."""
    organizerId: str
    name: str
    eventsCreated: int
    totalRegistrations: int
    averageAttendance: float


class AnalyticsData(BaseModel):
    """Complete analytics data."""
    summary: AnalyticsSummary
    byCategory: List[CategoryAnalytics]
    byDate: List[DateAnalytics]
    topEvents: List[TopEvent]
    organizerStats: List[OrganizerStats]


class AnalyticsResponse(BaseModel):
    """Schema for analytics response."""
    success: bool = True
    analytics: AnalyticsData


# ============================================================================
# DASHBOARD SCHEMAS
# ============================================================================

class DashboardStats(BaseModel):
    """Dashboard statistics."""
    pendingOrganizers: int
    pendingEvents: int
    totalPending: int
    totalEvents: int
    totalRegistrations: int
    totalAttendance: int
    activeOrganizers: int
    activeStudents: int


class DashboardResponse(BaseModel):
    """Schema for dashboard response."""
    success: bool = True
    stats: DashboardStats


# ============================================================================
# GENERIC SUCCESS RESPONSES
# ============================================================================

class AdminActionResponse(BaseModel):
    """Generic success response for admin actions."""
    success: bool = True
    message: str


class CategoryCreatedResponse(BaseModel):
    """Response for category creation."""
    success: bool = True
    message: str
    category: Dict[str, Any]


class VenueCreatedResponse(BaseModel):
    """Response for venue creation."""
    success: bool = True
    message: str
    venue: Dict[str, Any]
