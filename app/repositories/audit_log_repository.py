"""
Audit Log repository for database operations.
Handles all database interactions for AuditLog model.
This is an append-only repository - no updates or deletes allowed.
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.models.audit_log import AuditLog, AuditAction, TargetType
import uuid


class AuditLogRepository:
    """Repository for AuditLog database operations (append-only)."""
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_by_id(self, log_id: str) -> Optional[AuditLog]:
        """
        Get audit log by ID.
        
        Args:
            log_id: Log entry ID
            
        Returns:
            Optional[AuditLog]: Log entry if found, None otherwise
        """
        return self.db.query(AuditLog).filter(AuditLog.id == log_id).first()
    
    def get_all(
        self,
        action: Optional[AuditAction] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        actor_id: Optional[str] = None,
        target_type: Optional[TargetType] = None,
        target_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> Tuple[List[AuditLog], int]:
        """
        Get paginated list of audit logs with filters.
        
        Args:
            action: Filter by action type
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            actor_id: Filter by actor user ID
            target_type: Filter by target type
            target_id: Filter by target ID
            search: Search in details
            page: Page number (1-indexed)
            limit: Items per page
            
        Returns:
            Tuple[List[AuditLog], int]: List of logs and total count
        """
        query = self.db.query(AuditLog)
        
        # Apply filters
        if action:
            query = query.filter(AuditLog.action == action)
        
        if start_date:
            query = query.filter(AuditLog.timestamp >= datetime.combine(start_date, datetime.min.time()))
        
        if end_date:
            query = query.filter(AuditLog.timestamp <= datetime.combine(end_date, datetime.max.time()))
        
        if actor_id:
            query = query.filter(AuditLog.actor_id == actor_id)
        
        if target_type:
            query = query.filter(AuditLog.target_type == target_type)
        
        if target_id:
            query = query.filter(AuditLog.target_id == target_id)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(AuditLog.details.ilike(search_pattern))
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply sorting and pagination
        offset = (page - 1) * limit
        logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
        
        return logs, total_count
    
    def create(
        self,
        action: AuditAction,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None,
        actor_role: Optional[str] = None,
        target_type: Optional[TargetType] = None,
        target_id: Optional[str] = None,
        target_name: Optional[str] = None,
        details: Optional[str] = None,
        metadata: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Create a new audit log entry.
        
        Args:
            action: Action that was performed
            actor_id: User ID who performed action
            actor_name: User name who performed action
            actor_role: Role of user who performed action
            target_type: Type of target entity
            target_id: ID of target entity
            target_name: Name of target entity
            details: Human-readable description
            metadata: Additional metadata as dict
            ip_address: IP address of request
            user_agent: User agent of request
            
        Returns:
            AuditLog: Created log entry
        """
        log_id = str(uuid.uuid4())
        
        log = AuditLog(
            id=log_id,
            action=action,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_role=actor_role,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            details=details,
            extra_metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
    
    def get_by_actor(
        self,
        actor_id: str,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get recent logs for a specific actor.
        
        Args:
            actor_id: Actor user ID
            limit: Maximum number of logs to return
            
        Returns:
            List[AuditLog]: List of log entries
        """
        return self.db.query(AuditLog).filter(
            AuditLog.actor_id == actor_id
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    def get_by_target(
        self,
        target_type: TargetType,
        target_id: str,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get logs for a specific target.
        
        Args:
            target_type: Type of target
            target_id: Target ID
            limit: Maximum number of logs to return
            
        Returns:
            List[AuditLog]: List of log entries
        """
        return self.db.query(AuditLog).filter(
            AuditLog.target_type == target_type,
            AuditLog.target_id == target_id
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    def get_recent(self, limit: int = 100) -> List[AuditLog]:
        """
        Get most recent audit logs.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List[AuditLog]: List of recent log entries
        """
        return self.db.query(AuditLog).order_by(
            AuditLog.timestamp.desc()
        ).limit(limit).all()



    def count_by_action_and_actor(
        self,
        action: AuditAction,
        actor_id: str,
        since: datetime = None
    ) -> int:
        """
        Count audit logs by action and actor since a given time.

        Args:
            action: The audit action to count
            actor_id: The actor ID
            since: Optional datetime to count from (default: all time)

        Returns:
            int: Count of matching audit logs
        """
        query = self.db.query(AuditLog).filter(
            AuditLog.action == action,
            AuditLog.actor_id == actor_id
        )

        if since:
            query = query.filter(AuditLog.timestamp >= since)

        return query.count()
