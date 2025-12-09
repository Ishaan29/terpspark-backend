from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.user import User, UserRole
from app.core.security import get_password_hash
import uuid


class UserRepository:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.lower()).first()
    
    def create(
        self,
        email: str,
        password: str,
        name: str,
        role: UserRole = UserRole.STUDENT,
        department: Optional[str] = None,
        phone: Optional[str] = None
    ) -> User:
        user_id = str(uuid.uuid4())
        
        
        hashed_password = get_password_hash(password)
        
        
        user = User(
            id=user_id,
            email=email.lower(),
            password=hashed_password,
            name=name,
            role=role,
            department=department,
            phone=phone,
            is_approved=(role == UserRole.STUDENT or role == UserRole.ADMIN)
        )
        
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError:
            self.db.rollback()
            raise
    
    def update(self, user: User, **kwargs) -> User:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update_last_login(self, user: User) -> User:
        from datetime import datetime
        user.last_login = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def approve_organizer(self, user: User) -> User:
        user.is_approved = True
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def deactivate(self, user: User) -> User:
        user.is_active = False
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def activate(self, user: User) -> User:
        user.is_active = True
        self.db.commit()
        self.db.refresh(user)
        return user
