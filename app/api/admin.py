from sqlalchemy.orm import Session
from typing import Optional, List
import csv
import io
from datetime import datetime

from app.core.database import get_db
from app.middleware.auth import get_current_active_user
from app.services.admin_service import AdminService
from app.models.user import User
from app.schemas.admin import (
    OrganizerApprovalsResponse,
    ApprovalActionRequest,
    RejectionRequest,
    EventApprovalsResponse,
    AuditLogsResponse,
    AnalyticsResponse,
    DashboardResponse,
    AdminActionResponse,
    CategoryCreatedResponse,
    VenueCreatedResponse,
    OrganizerApprovalResponse,
    EventApprovalResponse,
    EventApprovalOrganizerInfo,
    EventApprovalCategoryInfo,
    AuditLogResponse,
    AuditLogActorInfo,
    AuditLogTargetInfo,
    PaginationInfo
)
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse, CategoriesResponse
from app.schemas.venue import VenueCreate, VenueUpdate, VenueResponse, VenuesResponse

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.get(
    "/approvals/organizers",
    response_model=OrganizerApprovalsResponse,
    summary="Get organizer approval requests"
)
async def get_organizer_approvals(
    status: str = Query("pending", description="Filter by status: pending, approved, rejected, all"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get pending organizer approval requests.

    **Requires:** Admin role

    **Query Parameters:**
    - status: 'pending', 'approved', 'rejected', or 'all' (default: 'pending')

    **Returns:**
    - List of organizer approval requests with user details
    """
    admin_service = AdminService(db)
    requests = admin_service.get_organizer_approvals(current_user, status_filter=status)

    # Convert to response format
    request_responses = []
    for req in requests:
        request_responses.append(OrganizerApprovalResponse(
            id=req.id,
            userId=req.user_id,
            name=req.user.name if req.user else "Unknown",
            email=req.user.email if req.user else "Unknown",
            department=req.user.department if req.user else None,
            reason=req.reason,
            requestedAt=req.requested_at.isoformat() if req.requested_at else None,
            status=req.status.value,
            reviewedBy=req.reviewed_by,
            reviewedAt=req.reviewed_at.isoformat() if req.reviewed_at else None,
            notes=req.notes
        ))

    return OrganizerApprovalsResponse(requests=request_responses)


@router.post(
    "/approvals/organizers/{request_id}/approve",
    response_model=AdminActionResponse,
    summary="Approve organizer request"
)
async def approve_organizer(
    request_id: str,
    approval_data: ApprovalActionRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Approve an organizer request.

    **Requires:** Admin role

    **Business Rules:**
    - Updates user's role to "organizer"
    - Sets isApproved to true
    - Sends approval notification email
    - Logs action in audit trail

    **Returns:**
    - Success message
    """
    admin_service = AdminService(db)
    admin_service.approve_organizer(
        request_id=request_id,
        admin=current_user,
        notes=approval_data.notes,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return AdminActionResponse(
        message="Organizer approved successfully. User role has been updated."
    )


@router.post(
    "/approvals/organizers/{request_id}/reject",
    response_model=AdminActionResponse,
    summary="Reject organizer request"
)
async def reject_organizer(
    request_id: str,
    rejection_data: RejectionRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Reject an organizer request.

    **Requires:** Admin role

    **Business Rules:**
    - Notes/reason required for rejection
    - Sends rejection notification with feedback
    - Logs action in audit trail

    **Returns:**
    - Success message
    """
    admin_service = AdminService(db)
    admin_service.reject_organizer(
        request_id=request_id,
        admin=current_user,
        notes=rejection_data.notes,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return AdminActionResponse(message="Organizer request rejected")


# ============================================================================
# 2. EVENT APPROVALS
# ============================================================================

@router.get(
    "/approvals/events",
    response_model=EventApprovalsResponse,
    summary="Get pending event submissions"
)
async def get_pending_events(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get pending event submissions.

    **Requires:** Admin role

    **Returns:**
    - List of events awaiting approval
    """
    admin_service = AdminService(db)
    events = admin_service.get_pending_events(current_user)

    # Convert to response format
    event_responses = []
    for event in events:
        event_responses.append(EventApprovalResponse(
            id=event.id,
            title=event.title,
            description=event.description,
            category=EventApprovalCategoryInfo(name=event.category.name) if event.category else EventApprovalCategoryInfo(name="Unknown"),
            organizer=EventApprovalOrganizerInfo(
                id=event.organizer.id if event.organizer else "",
                name=event.organizer.name if event.organizer else "Unknown",
                email=event.organizer.email if event.organizer else "Unknown"
            ),
            date=event.date.isoformat() if event.date else "",
            startTime=event.start_time.strftime("%H:%M") if event.start_time else "",
            endTime=event.end_time.strftime("%H:%M") if event.end_time else "",
            venue=event.venue,
            capacity=event.capacity,
            submittedAt=event.created_at.isoformat() if event.created_at else "",
            status=event.status.value
        ))

    return EventApprovalsResponse(events=event_responses)


@router.post(
    "/approvals/events/{event_id}/approve",
    response_model=AdminActionResponse,
    summary="Approve and publish event"
)
async def approve_event(
    event_id: str,
    approval_data: ApprovalActionRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Approve and publish an event.

    **Requires:** Admin role

    **Business Rules:**
    - Changes event status to "published"
    - Sets publishedAt timestamp
    - Notifies organizer of approval
    - Event becomes visible to students
    - Logs action in audit trail

    **Returns:**
    - Success message
    """
    admin_service = AdminService(db)
    admin_service.approve_event(
        event_id=event_id,
        admin=current_user,
        notes=approval_data.notes,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return AdminActionResponse(message="Event approved and published")


@router.post(
    "/approvals/events/{event_id}/reject",
    response_model=AdminActionResponse,
    summary="Reject event submission"
)
async def reject_event(
    event_id: str,
    rejection_data: RejectionRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Reject an event submission.

    **Requires:** Admin role

    **Business Rules:**
    - Changes event status to "rejected"
    - Notes/reason required
    - Notifies organizer with feedback
    - Logs action in audit trail

    **Returns:**
    - Success message
    """
    admin_service = AdminService(db)
    admin_service.reject_event(
        event_id=event_id,
        admin=current_user,
        notes=rejection_data.notes,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return AdminActionResponse(message="Event rejected")


@router.get(
    "/categories",
    response_model=CategoriesResponse,
    summary="Get all categories"
)
async def get_all_categories(
    includeInactive: bool = Query(True, description="Include inactive categories"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all categories (including inactive).

    **Requires:** Admin role

    **Returns:**
    - List of all categories
    """
    admin_service = AdminService(db)
    categories = admin_service.get_all_categories(current_user, include_inactive=includeInactive)

    # Convert to response format
    category_responses = [CategoryResponse(
        id=cat.id,
        name=cat.name,
        slug=cat.slug,
        description=cat.description,
        color=cat.color,
        icon=cat.icon,
        isActive=cat.is_active,
        createdAt=cat.created_at.isoformat() if cat.created_at else None,
        updatedAt=cat.updated_at.isoformat() if cat.updated_at else None
    ) for cat in categories]

    return CategoriesResponse(categories=category_responses)


@router.post(
    "/categories",
    response_model=CategoryCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new category"
)
async def create_category(
    category_data: CategoryCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new category.

    **Requires:** Admin role

    **Business Rules:**
    - Slug must be unique
    - Auto-generates slug from name if not provided
    - Logs action in audit trail

    **Returns:**
    - Created category
    """
    admin_service = AdminService(db)
    category = admin_service.create_category(
        admin=current_user,
        name=category_data.name,
        color=category_data.color,
        slug=category_data.slug,
        description=category_data.description,
        icon=category_data.icon,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return CategoryCreatedResponse(
        message="Category created successfully",
        category=category.to_dict()
    )


@router.put(
    "/categories/{category_id}",
    response_model=CategoryCreatedResponse,
    summary="Update category"
)
async def update_category(
    category_id: str,
    category_data: CategoryUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a category.

    **Requires:** Admin role

    **Returns:**
    - Updated category
    """
    admin_service = AdminService(db)
    category = admin_service.update_category(
        category_id=category_id,
        admin=current_user,
        name=category_data.name,
        description=category_data.description,
        color=category_data.color,
        icon=category_data.icon,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return CategoryCreatedResponse(
        message="Category updated successfully",
        category=category.to_dict()
    )


@router.delete(
    "/categories/{category_id}",
    response_model=AdminActionResponse,
    summary="Retire/reactivate category"
)
async def toggle_category(
    category_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retire/reactivate a category (soft delete).

    **Requires:** Admin role

    **Business Rules:**
    - Soft delete - toggles isActive flag
    - Doesn't actually delete (data preservation)
    - Cannot retire if events are using it
    - Logs action in audit trail

    **Returns:**
    - Success message
    """
    admin_service = AdminService(db)
    category = admin_service.toggle_category(
        category_id=category_id,
        admin=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    action = "retired" if not category.is_active else "reactivated"
    return AdminActionResponse(message=f"Category {action} successfully")


@router.get(
    "/venues",
    response_model=VenuesResponse,
    summary="Get all venues"
)
async def get_all_venues(
    includeInactive: bool = Query(True, description="Include inactive venues"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all venues.

    **Requires:** Admin role

    **Returns:**
    - List of all venues
    """
    admin_service = AdminService(db)
    venues = admin_service.get_all_venues(current_user, include_inactive=includeInactive)

    # Convert to response format
    venue_responses = [VenueResponse(
        id=venue.id,
        name=venue.name,
        building=venue.building,
        capacity=venue.capacity,
        facilities=venue.facilities if venue.facilities else [],
        isActive=venue.is_active,
        createdAt=venue.created_at.isoformat() if venue.created_at else None,
        updatedAt=venue.updated_at.isoformat() if venue.updated_at else None
    ) for venue in venues]

    return VenuesResponse(venues=venue_responses)


@router.post(
    "/venues",
    response_model=VenueCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new venue"
)
async def create_venue(
    venue_data: VenueCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new venue.

    **Requires:** Admin role

    **Returns:**
    - Created venue
    """
    admin_service = AdminService(db)
    venue = admin_service.create_venue(
        admin=current_user,
        name=venue_data.name,
        building=venue_data.building,
        capacity=venue_data.capacity,
        facilities=venue_data.facilities,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return VenueCreatedResponse(
        message="Venue created successfully",
        venue=venue.to_dict()
    )


@router.put(
    "/venues/{venue_id}",
    response_model=VenueCreatedResponse,
    summary="Update venue"
)
async def update_venue(
    venue_id: str,
    venue_data: VenueUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a venue.

    **Requires:** Admin role

    **Returns:**
    - Updated venue
    """
    admin_service = AdminService(db)
    venue = admin_service.update_venue(
        venue_id=venue_id,
        admin=current_user,
        name=venue_data.name,
        building=venue_data.building,
        capacity=venue_data.capacity,
        facilities=venue_data.facilities,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return VenueCreatedResponse(
        message="Venue updated successfully",
        venue=venue.to_dict()
    )


@router.delete(
    "/venues/{venue_id}",
    response_model=AdminActionResponse,
    summary="Retire/reactivate venue"
)
async def toggle_venue(
    venue_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retire/reactivate a venue.

    **Requires:** Admin role

    **Returns:**
    - Success message
    """
    admin_service = AdminService(db)
    venue = admin_service.toggle_venue(
        venue_id=venue_id,
        admin=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    action = "retired" if not venue.is_active else "reactivated"
    return AdminActionResponse(message=f"Venue {action} successfully")


# ============================================================================
# 5. AUDIT LOGS
# ============================================================================

@router.get(
    "/audit-logs",
    response_model=AuditLogsResponse,
    summary="Get audit log entries"
)
async def get_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    startDate: Optional[str] = Query(None, description="Filter by start date (ISO 8601)"),
    endDate: Optional[str] = Query(None, description="Filter by end date (ISO 8601)"),
    userId: Optional[str] = Query(None, description="Filter by user ID"),
    search: Optional[str] = Query(None, description="Search in details"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get audit log entries (read-only).

    **Requires:** Admin role

    **Query Parameters:**
    - action: Filter by action type
    - startDate: ISO 8601 date
    - endDate: ISO 8601 date
    - userId: Filter by user
    - search: Search in details
    - page: Pagination page number
    - limit: Items per page (max 100)

    **Business Rules:**
    - Append-only (cannot edit or delete)
    - Must log all sensitive actions
    - Include IP address and user agent

    **Returns:**
    - Paginated list of audit log entries
    """
    admin_service = AdminService(db)
    logs, total_count = admin_service.get_audit_logs(
        admin=current_user,
        action=action,
        start_date=startDate,
        end_date=endDate,
        user_id=userId,
        search=search,
        page=page,
        limit=limit
    )

    # Convert to response format
    log_responses = []
    for log in logs:
        log_responses.append(AuditLogResponse(
            id=log.id,
            timestamp=log.timestamp.isoformat() if log.timestamp else "",
            action=log.action.value,
            actor=AuditLogActorInfo(
                id=log.actor_id,
                name=log.actor_name,
                role=log.actor_role
            ),
            target=AuditLogTargetInfo(
                type=log.target_type.value,
                id=log.target_id,
                name=log.target_name
            ),
            details=log.details,
            ipAddress=log.ip_address,
            userAgent=log.user_agent,
            metadata=log.metadata if isinstance(log.metadata, dict) else None
        ))

    # Calculate pagination
    total_pages = (total_count + limit - 1) // limit
    pagination = PaginationInfo(
        currentPage=page,
        totalPages=total_pages,
        totalItems=total_count,
        itemsPerPage=limit
    )

    return AuditLogsResponse(logs=log_responses, pagination=pagination)


@router.get(
    "/audit-logs/export",
    summary="Export audit logs as CSV"
)
async def export_audit_logs(
    action: Optional[str] = Query(None),
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    userId: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export audit logs as CSV.

    **Requires:** Admin role

    **Returns:**
    - CSV file with all audit log entries
    """
    admin_service = AdminService(db)

    # Get all logs (no pagination for export)
    logs, _ = admin_service.get_audit_logs(
        admin=current_user,
        action=action,
        start_date=startDate,
        end_date=endDate,
        user_id=userId,
        search=search,
        page=1,
        limit=10000  # Large limit for export
    )

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "ID",
        "Timestamp",
        "Action",
        "Actor ID",
        "Actor Name",
        "Actor Role",
        "Target Type",
        "Target ID",
        "Target Name",
        "Details",
        "IP Address",
        "User Agent"
    ])

    # Data rows
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.isoformat() if log.timestamp else "",
            log.action.value,
            log.actor_id,
            log.actor_name,
            log.actor_role,
            log.target_type.value,
            log.target_id,
            log.target_name,
            log.details,
            log.ip_address or "",
            log.user_agent or ""
        ])

    # Return CSV file
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )



@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    summary="Get system-wide analytics"
)
async def get_analytics(
    startDate: Optional[str] = Query(None, description="Filter by start date (ISO 8601)"),
    endDate: Optional[str] = Query(None, description="Filter by end date (ISO 8601)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get system-wide analytics.

    **Requires:** Admin role

    **Returns:**
    - Comprehensive analytics including:
      - Summary statistics
      - Analytics by category
      - Analytics by date
      - Top performing events
      - Organizer statistics
    """
    admin_service = AdminService(db)
    analytics_data = admin_service.get_analytics(
        admin=current_user,
        start_date=startDate,
        end_date=endDate,
        category=category
    )

    return AnalyticsResponse(analytics=analytics_data)


@router.get(
    "/analytics/export",
    summary="Export analytics as CSV"
)
async def export_analytics(
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Export analytics data as CSV.

    **Requires:** Admin role

    **Returns:**
    - CSV file with analytics data
    """
    admin_service = AdminService(db)
    analytics_data = admin_service.get_analytics(
        admin=current_user,
        start_date=startDate,
        end_date=endDate,
        category=category
    )

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Write summary
    writer.writerow(["Summary Statistics"])
    writer.writerow(["Metric", "Value"])
    summary = analytics_data["summary"]
    for key, value in summary.items():
        writer.writerow([key, value])

    # Return CSV file
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Get admin dashboard statistics"
)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get admin dashboard statistics.

    **Requires:** Admin role

    **Returns:**
    - Dashboard statistics including:
      - Pending organizers count
      - Pending events count
      - Total pending items
      - Total events
      - Total registrations
      - Total attendance
      - Active organizers
      - Active students
    """
    admin_service = AdminService(db)
    stats = admin_service.get_dashboard_stats(current_user)

    return DashboardResponse(stats=stats)
