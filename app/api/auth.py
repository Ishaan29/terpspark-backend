from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.middleware.auth import get_current_user, get_current_active_user
from app.models.user import User
from app.schemas.auth import (
    UserLogin,
    UserCreate,
    UserResponse,
    TokenResponse,
    TokenValidateResponse,
    LogoutResponse,
    ErrorResponse
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        403: {"model": ErrorResponse, "description": "Account not approved or deactivated"}
    }
)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate user with email and password.
    
    **Business Rules:**
    - Email must be valid UMD email (@umd.edu)
    - Organizers must have isApproved: true to login
    - User must be active
    - Generates JWT token with 24-hour expiration
    
    **Returns:**
    - User information and JWT access token
    
    **Error Codes:**
    - `INVALID_CREDENTIALS`: Invalid email or password
    - `ORGANIZER_NOT_APPROVED`: Organizer account pending approval
    - `ACCOUNT_DEACTIVATED`: User account is deactivated
    """
    auth_service = AuthService(db)
    
    try:
        user, token = auth_service.authenticate_user(credentials)
        
        return TokenResponse(
            success=True,
            user=UserResponse.model_validate(user.to_dict()),
            token=token,
            token_type="bearer"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Validation error"}
    }
)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user.

    **Business Rules:**
    - Email must be valid UMD email (@umd.edu)
    - Password must be at least 8 characters
    - Students are auto-approved
    - Organizers require admin approval (automatically creates approval request)
    - Admins are auto-approved (should be created manually)

    **Organizer Registration Flow:**
    - When an organizer registers, an `OrganizerApprovalRequest` is automatically created
    - The request appears in the admin approval queue (`/api/admin/approvals/organizers`)
    - The organizer account has `isApproved: false` until admin approves
    - Organizers cannot login until their account is approved

    **Returns:**
    - Created user information and JWT access token

    **Error Codes:**
    - `EMAIL_ALREADY_EXISTS`: Email is already registered
    - `INVALID_EMAIL`: Email is not a valid UMD email
    """
    auth_service = AuthService(db)
    
    try:
        user = auth_service.register_user(user_data)
        
        # Automatically log in the user
        from app.core.security import create_access_token
        token_data = {
            "sub": user.id,
            "email": user.email,
            "role": user.role.value,
            "is_approved": user.is_approved
        }
        token = create_access_token(token_data)
        
        return TokenResponse(
            success=True,
            user=UserResponse.model_validate(user.to_dict()),
            token=token,
            token_type="bearer"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    }
)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Log out the current user.
    
    **Note:** JWT tokens are stateless, so logout is handled client-side
    by removing the token. This endpoint confirms the token is valid
    and can be used for server-side cleanup if needed.
    
    **Business Rules:**
    - Requires valid JWT token
    - Token should be invalidated client-side
    
    **Returns:**
    - Success message
    """
    
    return LogoutResponse(
        success=True,
        message="Logged out successfully"
    )


@router.get(
    "/validate",
    response_model=TokenValidateResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired token"}
    }
)
async def validate_token(
    current_user: User = Depends(get_current_user)
):
    """
    Validate the current session token.
    
    **Business Rules:**
    - Verifies JWT token signature and expiration
    - Returns user data if valid
    
    **Returns:**
    - Validation status and user information
    """
    return TokenValidateResponse(
        valid=True,
        user=UserResponse.model_validate(current_user.to_dict())
    )


@router.get(
    "/user",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    }
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user's details.
    
    **Business Rules:**
    - Requires valid JWT token
    - Returns full user profile information
    
    **Returns:**
    - Current user information
    """
    return UserResponse.model_validate(current_user.to_dict())


# Health check endpoint (no auth required)
@router.get("/health")
async def health_check():
    """
    Health check endpoint to verify API is running.
    
    **Returns:**
    - API status
    """
    return {
        "status": "healthy",
        "service": "TerpSpark Auth API",
        "version": "1.0.0"
    }
