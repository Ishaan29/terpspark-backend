"""
Pydantic schemas for registration requests and responses.
Provides data validation and serialization for registration endpoints.
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List


class GuestInfo(BaseModel):
    """Guest information."""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    
    @validator('email')
    def validate_umd_email(cls, v):
        """Ensure email is a UMD email address."""
        email_lower = v.lower()
        if not (email_lower.endswith('@umd.edu') or email_lower.endswith('@terpmail.umd.edu')):
            raise ValueError('Guest email must be a valid UMD email address (@umd.edu or @terpmail.umd.edu)')
        return email_lower


class RegistrationCreate(BaseModel):
    """Schema for creating a new registration."""
    eventId: str
    guests: Optional[List[GuestInfo]] = Field(default_factory=list, max_items=2, description="Maximum 2 guests")
    sessions: Optional[List[str]] = Field(default_factory=list, description="Session IDs for multi-session events")
    notificationPreference: Optional[str] = Field("email", pattern="^(email|sms|both|none)$")


class EventBasicInfo(BaseModel):
    """Basic event information in registration response."""
    id: str
    title: str
    date: str
    startTime: str
    venue: str
    organizer: dict


class RegistrationResponse(BaseModel):
    """Schema for registration data in responses."""
    id: str
    userId: str
    eventId: str
    status: str
    ticketCode: str
    qrCode: Optional[str] = None
    registeredAt: str
    checkInStatus: str
    checkedInAt: Optional[str] = None
    guests: List[dict] = []
    sessions: List[str] = []
    reminderSent: bool
    cancelledAt: Optional[str] = None
    event: Optional[EventBasicInfo] = None
    
    class Config:
        from_attributes = True


class RegistrationCreateResponse(BaseModel):
    """Schema for registration creation response."""
    success: bool = True
    message: str = "Successfully registered for event"
    registration: RegistrationResponse


class RegistrationsListResponse(BaseModel):
    """Schema for list of registrations response."""
    success: bool = True
    registrations: List[RegistrationResponse]


class AttendeeInfo(BaseModel):
    """Attendee information for organizer view."""
    id: str
    registrationId: str
    name: str
    email: str
    registeredAt: str
    checkInStatus: str
    checkedInAt: Optional[str] = None
    guests: List[dict] = []


class AttendeeStatistics(BaseModel):
    """Statistics for event attendees."""
    totalRegistrations: int
    checkedIn: int
    notCheckedIn: int
    totalAttendees: int
    capacityUsed: str


class AttendeesResponse(BaseModel):
    """Schema for event attendees response."""
    success: bool = True
    attendees: List[AttendeeInfo]
    statistics: AttendeeStatistics

