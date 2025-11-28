"""
Pydantic schemas for authentication requests and responses.
Provides data validation and serialization for auth endpoints.
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=255)
    
    @validator('email')
    def validate_umd_email(cls, v):
        """Ensure email is a UMD email address."""
        email_lower = v.lower()
        if not (email_lower.endswith('@umd.edu') or email_lower.endswith('@terpmail.umd.edu')):
            raise ValueError('Email must be a valid UMD email address (@umd.edu or @terpmail.umd.edu)')
        return email_lower


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.STUDENT
    department: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user data in responses."""
    id: str
    email: str
    name: str
    role: str
    isApproved: bool
    isActive: bool
    phone: Optional[str] = None
    department: Optional[str] = None
    profilePicture: Optional[str] = None
    graduationYear: Optional[str] = None
    bio: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    lastLogin: Optional[str] = None
    
    class Config:
        from_attributes = True  # Allows conversion from ORM models


class TokenResponse(BaseModel):
    """Schema for token response after login."""
    success: bool = True
    user: UserResponse
    token: str
    token_type: str = "bearer"


class TokenValidateResponse(BaseModel):
    """Schema for token validation response."""
    valid: bool
    user: Optional[UserResponse] = None


class LogoutResponse(BaseModel):
    """Schema for logout response."""
    success: bool = True
    message: str = "Logged out successfully"


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    success: bool = False
    error: str
    code: Optional[str] = None
    details: Optional[dict] = None


class MessageResponse(BaseModel):
    """Generic success message response."""
    success: bool = True
    message: str
