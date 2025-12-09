from pydantic import BaseModel, Field
from typing import Optional


class WaitlistCreate(BaseModel):
    eventId: str
    notificationPreference: str = Field("email", pattern="^(email|sms|both)$")


class EventWaitlistInfo(BaseModel):
    id: str
    title: str
    date: str
    capacity: int
    registeredCount: int


class WaitlistResponse(BaseModel):
    id: str
    userId: str
    eventId: str
    position: int
    joinedAt: str
    notificationPreference: str
    event: Optional[EventWaitlistInfo] = None
    
    class Config:
        from_attributes = True


class WaitlistCreateResponse(BaseModel):
    success: bool = True
    message: str
    waitlistEntry: WaitlistResponse


class WaitlistListResponse(BaseModel):
    success: bool = True
    waitlist: list[WaitlistResponse]

