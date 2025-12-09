from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    
    token = credentials.credentials
    
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (alias for get_current_user).
    
    Args:
        current_user: Current user from token
        
    Returns:
        User: Current active user
    """
    return current_user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory to require specific user roles.
    
    Usage:
        @router.get("/admin-only")
        def admin_endpoint(user: User = Depends(require_role(UserRole.ADMIN))):
            return {"message": "Admin access granted"}
    
    Args:
        *allowed_roles: Allowed user roles
        
    Returns:
        Dependency function that checks user role
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[role.value for role in allowed_roles]}"
            )
        return current_user
    
    return role_checker


def require_approved_organizer():
    """
    Dependency to require approved organizer.
    
    Returns:
        Dependency function that checks organizer approval
    """
    async def approval_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != UserRole.ORGANIZER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organizer role required"
            )
        
        if not current_user.is_approved:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your organizer account is pending approval"
            )
        
        return current_user
    
    return approval_checker



async def require_student(
    current_user: User = Depends(require_role(UserRole.STUDENT, UserRole.ORGANIZER, UserRole.ADMIN))
) -> User:
    """Require student, organizer, or admin role."""
    return current_user


async def require_organizer(
    current_user: User = Depends(require_role(UserRole.ORGANIZER, UserRole.ADMIN))
) -> User:
    """Require organizer or admin role."""
    if current_user.role == UserRole.ORGANIZER and not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your organizer account is pending approval"
        )
    return current_user


async def require_admin(
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> User:
    """Require admin role."""
    return current_user



async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if token is provided, None otherwise.
    Useful for endpoints that show different data for authenticated vs anonymous users.
    
    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session
        
    Returns:
        Optional[User]: Current user if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
