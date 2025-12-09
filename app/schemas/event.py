from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, time


class EventBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=50)
    categoryId: str
    venue: str = Field(..., min_length=2, max_length=200)
    location: str = Field(..., min_length=5, max_length=500)
    capacity: int = Field(..., ge=1, le=5000, description="Maximum capacity (1-5000)")
    imageUrl: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = Field(default_factory=list)


class EventCreate(EventBase):
    date: str = Field(..., description="Event date in YYYY-MM-DD format")
    startTime: str = Field(..., description="Start time in HH:MM format (24-hour)")
    endTime: str = Field(..., description="End time in HH:MM format (24-hour)")
    
    @validator('date')
    def validate_date(cls, v):
        try:
            event_date = date.fromisoformat(v)
            if event_date < date.today():
                raise ValueError('Event date must be in the future')
            return v
        except ValueError as e:
            if 'future' in str(e):
                raise
            raise ValueError('Date must be in YYYY-MM-DD format')
    
    @validator('startTime', 'endTime')
    def validate_time(cls, v):
        try:
            time.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError('Time must be in HH:MM format (24-hour)')
    
    @validator('endTime')
    def validate_end_time(cls, v, values):
        if 'startTime' in values:
            start = time.fromisoformat(values['startTime'])
            end = time.fromisoformat(v)
            if end <= start:
                raise ValueError('End time must be after start time')
        return v


class EventUpdate(EventCreate):
    status: Optional[str] = Field(None, description="Event status (draft, pending, published, cancelled)")

class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    description: Optional[str] = Field(None, min_length=50)
    categoryId: Optional[str] = None
    date: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    venue: Optional[str] = Field(None, min_length=2, max_length=200)
    location: Optional[str] = Field(None, min_length=5, max_length=500)
    capacity: Optional[int] = Field(None, ge=1, le=5000)
    imageUrl: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = None


class OrganizerInfo(BaseModel):
    id: str
    name: str
    email: str
    department: Optional[str] = None


class CategoryInfo(BaseModel):
    id: str
    name: str
    slug: str
    color: str


class EventResponse(BaseModel):
    id: str
    title: str
    description: str
    categoryId: str
    organizerId: str
    date: str
    startTime: str
    endTime: str
    venue: str
    location: str
    capacity: int
    registeredCount: int
    waitlistCount: int
    remainingCapacity: int
    status: str
    imageUrl: Optional[str] = None
    tags: List[str] = []
    isFeatured: bool
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    publishedAt: Optional[str] = None
    cancelledAt: Optional[str] = None
    category: Optional[CategoryInfo] = None
    organizer: Optional[OrganizerInfo] = None
    
    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    id: str
    title: str
    description: str
    category: CategoryInfo
    organizer: OrganizerInfo
    date: str
    startTime: str
    endTime: str
    venue: str
    location: str
    capacity: int
    registeredCount: int
    waitlistCount: int
    status: str
    imageUrl: Optional[str] = None
    tags: List[str] = []
    isFeatured: bool
    createdAt: Optional[str] = None
    publishedAt: Optional[str] = None
    
    class Config:
        from_attributes = True


class PaginationInfo(BaseModel):
    currentPage: int
    totalPages: int
    totalItems: int
    itemsPerPage: int


class EventsListResponse(BaseModel):
    success: bool = True
    events: List[EventListResponse]
    pagination: PaginationInfo


class EventDetailResponse(BaseModel):
    success: bool = True
    event: EventResponse


class EventStatistics(BaseModel):
    total: int
    draft: int = 0
    pending: int = 0
    published: int = 0
    cancelled: int = 0


class OrganizerEventsResponse(BaseModel):
    success: bool = True
    events: List[EventResponse]
    statistics: EventStatistics

