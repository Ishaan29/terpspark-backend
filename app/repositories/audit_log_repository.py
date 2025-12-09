from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.models.audit_log import AuditLog, AuditAction, TargetType
import uuid


class AuditLogRepository:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, log_id: str) -> Optional[AuditLog]:
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
        query = self.db.query(AuditLog)
        
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
        
        total_count = query.count()
        
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
        return self.db.query(AuditLog).filter(
            AuditLog.actor_id == actor_id
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    def get_by_target(
        self,
        target_type: TargetType,
        target_id: str,
        limit: int = 100
    ) -> List[AuditLog]:
        return self.db.query(AuditLog).filter(
            AuditLog.target_type == target_type,
            AuditLog.target_id == target_id
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    def get_recent(self, limit: int = 100) -> List[AuditLog]:
        return self.db.query(AuditLog).order_by(
            AuditLog.timestamp.desc()
        ).limit(limit).all()



    def count_by_action_and_actor(
        self,
        action: AuditAction,
        actor_id: str,
        since: datetime = None
    ) -> int:
        query = self.db.query(AuditLog).filter(
            AuditLog.action == action,
            AuditLog.actor_id == actor_id
        )

        if since:
            query = query.filter(AuditLog.timestamp >= since)

        return query.count()
