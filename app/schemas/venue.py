from pydantic import BaseModel, Field
from typing import Optional, List


class VenueBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    building: str = Field(..., min_length=2, max_length=200)
    capacity: Optional[int] = Field(None, ge=1, description="Maximum capacity")
    facilities: Optional[List[str]] = Field(default_factory=list)


class VenueCreate(VenueBase):
    pass


class VenueUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    building: Optional[str] = Field(None, min_length=2, max_length=200)
    capacity: Optional[int] = Field(None, ge=1)
    facilities: Optional[List[str]] = None


class VenueResponse(BaseModel):
    id: str
    name: str
    building: str
    capacity: Optional[int] = None
    facilities: List[str] = []
    isActive: bool
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    
    class Config:
        from_attributes = True


class VenuesResponse(BaseModel):
    success: bool = True
    venues: List[VenueResponse]

