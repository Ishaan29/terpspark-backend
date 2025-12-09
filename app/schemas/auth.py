from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=255)
    
    @validator('email')
    def validate_umd_email(cls, v):
        email_lower = v.lower()
        if not (email_lower.endswith('@umd.edu') or email_lower.endswith('@terpmail.umd.edu')):
            raise ValueError('Email must be a valid UMD email address (@umd.edu or @terpmail.umd.edu)')
        return email_lower


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.STUDENT
    department: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
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
        from_attributes = True


class TokenResponse(BaseModel):
    success: bool = True
    user: UserResponse
    token: str
    token_type: str = "bearer"


class TokenValidateResponse(BaseModel):
    valid: bool
    user: Optional[UserResponse] = None


class LogoutResponse(BaseModel):
    success: bool = True
    message: str = "Logged out successfully"


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    code: Optional[str] = None
    details: Optional[dict] = None


class MessageResponse(BaseModel):
    success: bool = True
    message: str
