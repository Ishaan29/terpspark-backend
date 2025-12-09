from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List


class GuestInfo(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    
    @validator('email')
    def validate_umd_email(cls, v):
        if not v.lower().endswith('@umd.edu'):
            raise ValueError('Guest email must be a valid UMD email address (@umd.edu)')
        return v.lower()


class RegistrationCreate(BaseModel):
    eventId: str
    guests: Optional[List[GuestInfo]] = Field(default_factory=list, max_items=2, description="Maximum 2 guests")
    sessions: Optional[List[str]] = Field(default_factory=list, description="Session IDs for multi-session events")
    notificationPreference: Optional[str] = Field("email", pattern="^(email|sms|both|none)$")


class EventBasicInfo(BaseModel):
    id: str
    title: str
    date: str
    startTime: str
    venue: str
    organizer: dict


class RegistrationResponse(BaseModel):
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
    success: bool = True
    message: str = "Successfully registered for event"
    registration: RegistrationResponse


class RegistrationsListResponse(BaseModel):
    success: bool = True
    registrations: List[RegistrationResponse]


class AttendeeInfo(BaseModel):
    id: str
    registrationId: str
    name: str
    email: str
    registeredAt: str
    checkInStatus: str
    checkedInAt: Optional[str] = None
    guests: List[dict] = []


class AttendeeStatistics(BaseModel):
    totalRegistrations: int
    checkedIn: int
    notCheckedIn: int
    totalAttendees: int
    capacityUsed: str


class AttendeesResponse(BaseModel):
    success: bool = True
    attendees: List[AttendeeInfo]
    statistics: AttendeeStatistics

