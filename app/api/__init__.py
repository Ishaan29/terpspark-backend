"""
API router initialization.
Aggregates all API route modules.
"""
from fastapi import APIRouter
from app.api import auth, events, registrations, waitlist, organizer

# Create main API router
api_router = APIRouter()

# Include authentication routes (Phase 1)
api_router.include_router(auth.router)

# Include event routes (Phase 2: Event Discovery & Browse)
api_router.include_router(events.router)

# Include registration routes (Phase 3: Student Registration Flow)
api_router.include_router(registrations.router)

# Include waitlist routes (Phase 3: Student Registration Flow)
api_router.include_router(waitlist.router)

# Include organizer routes (Phase 4: Organizer Management)
api_router.include_router(organizer.router)

# Future phase routers will be added here:
# from app.api import admin
# api_router.include_router(admin.router)
