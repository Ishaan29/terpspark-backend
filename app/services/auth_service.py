from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.repositories.organizer_approval_repository import OrganizerApprovalRepository
from app.core.security import verify_password, create_access_token
from app.schemas.auth import UserLogin, UserCreate


class AuthService:
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.approval_repo = OrganizerApprovalRepository(db)
    
    def authenticate_user(self, credentials: UserLogin) -> Tuple[User, str]:
        user = self.user_repo.get_by_email(credentials.email)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials. Please check your email and password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not verify_password(credentials.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials. Please check your email and password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.can_login:
            if user.is_organizer and not user.is_approved:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your organizer account is pending approval. Please contact an administrator."
                )
            elif not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your account has been deactivated. Please contact an administrator."
                )
        
        self.user_repo.update_last_login(user)
        
        token_data = {
            "sub": user.id,
            "email": user.email,
            "role": user.role.value,
            "is_approved": user.is_approved
        }
        token = create_access_token(token_data)
        
        return user, token
    
    def register_user(self, user_data: UserCreate) -> User:
        existing_user = self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered."
            )
        
        try:
            user = self.user_repo.create(
                email=user_data.email,
                password=user_data.password,
                name=user_data.name,
                role=user_data.role,
                department=user_data.department,
                phone=user_data.phone
            )

            if user.role == UserRole.ORGANIZER:
                reason = (
                    f"User {user.name} ({user.email}) from {user.department} department "
                    "requested organizer access during registration."
                )
                self.approval_repo.create(
                    user_id=user.id,
                    reason=reason
                )

            return user
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {str(e)}"
            )
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.user_repo.get_by_id(user_id)
