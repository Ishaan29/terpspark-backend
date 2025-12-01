# TerpSpark Backend API Documentation
## Complete Phase-by-Phase Backend API Requirements

---

## Table of Contents
1. [Phase 1: Authentication & User Management](#phase-1-authentication--user-management)
2. [Phase 2: Event Discovery & Browse](#phase-2-event-discovery--browse)
3. [Phase 3: Student Registration Flow](#phase-3-student-registration-flow)
4. [Phase 4: Organizer Event Management](#phase-4-organizer-event-management)
5. [Phase 5: Admin Console & Management](#phase-5-admin-console--management)
6. [Common Data Models](#common-data-models)
7. [Error Handling Standards](#error-handling-standards)

---

# Phase 1: Authentication & User Management

## Overview
Phase 1 provides the foundation with SSO-style authentication, session management, and role-based access control for three user types: Student, Organizer, and Admin.

## API Endpoints

### 1. User Authentication

#### POST `/api/auth/login`
Authenticate user with email and password (SSO-style).

**Request Body:**
```json
{
  "email": "string (required, must end with @umd.edu)",
  "password": "string (required)"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "user": {
    "id": "string",
    "email": "string",
    "name": "string",
    "role": "student | organizer | admin",
    "isApproved": "boolean (for organizers)",
    "createdAt": "ISO 8601 timestamp"
  },
  "token": "JWT token string"
}
```

**Error Response (401):**
```json
{
  "success": false,
  "error": "Invalid credentials. Please check your email and password."
}
```

**Error Response (403) - Organizer Not Approved:**
```json
{
  "success": false,
  "error": "Your organizer account is pending approval. Please contact an administrator."
}
```

**Business Rules:**
- Email must be valid UMD email (@umd.edu)
- Organizers must have `isApproved: true` to login
- Generate JWT token with reasonable expiration (e.g., 24 hours)
- Password should be hashed using bcrypt or similar

---

#### POST `/api/auth/logout`
Log out the current user and invalidate their session.

**Headers:**
```
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

**Business Rules:**
- Invalidate the JWT token
- Clear any server-side session data

---

#### GET `/api/auth/validate`
Validate the current session token.

**Headers:**
```
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "valid": true,
  "user": {
    "id": "string",
    "email": "string",
    "name": "string",
    "role": "student | organizer | admin"
  }
}
```

**Error Response (401):**
```json
{
  "valid": false
}
```

**Business Rules:**
- Verify JWT token signature and expiration
- Return user data if valid

---

#### GET `/api/auth/user`
Get current authenticated user's details.

**Headers:**
```
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "success": true,
  "user": {
    "id": "string",
    "email": "string",
    "name": "string",
    "role": "student | organizer | admin",
    "isApproved": "boolean (for organizers)",
    "department": "string (optional)",
    "phone": "string (optional)",
    "createdAt": "ISO 8601 timestamp",
    "updatedAt": "ISO 8601 timestamp"
  }
}
```

---

## User Data Model

```typescript
interface User {
  id: string;
  email: string;         // Must end with @umd.edu
  password: string;      // Hashed, never returned to client
  name: string;
  role: 'student' | 'organizer' | 'admin';
  isApproved: boolean;   // For organizers only
  department?: string;
  phone?: string;
  createdAt: string;     // ISO 8601 timestamp
  updatedAt: string;     // ISO 8601 timestamp
}
```

---

# Phase 2: Event Discovery & Browse

## Overview
Phase 2 adds event browsing, search, filtering, and detail viewing capabilities for all users.

## API Endpoints

### 1. Event Catalog

#### GET `/api/events`
Retrieve paginated list of published events with optional filters.

**Query Parameters:**
```
search?: string          // Search in title, description, tags, venue, organizer
category?: string        // Category slug (academic, career, cultural, etc.)
startDate?: string       // ISO 8601 date (filter events after this date)
endDate?: string         // ISO 8601 date (filter events before this date)
organizer?: string       // Organizer name search
availability?: boolean   // If true, only show events with available spots
sortBy?: string         // 'date' | 'title' | 'popularity' (default: 'date')
page?: number           // Page number (default: 1)
limit?: number          // Items per page (default: 20)
```

**Success Response (200):**
```json
{
  "success": true,
  "events": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "category": {
        "id": "string",
        "name": "string",
        "slug": "string",
        "color": "string"
      },
      "organizer": {
        "id": "string",
        "name": "string",
        "email": "string"
      },
      "date": "YYYY-MM-DD",
      "startTime": "HH:MM (24-hour)",
      "endTime": "HH:MM (24-hour)",
      "venue": "string",
      "location": "string",
      "capacity": "number",
      "registeredCount": "number",
      "waitlistCount": "number",
      "status": "published",
      "imageUrl": "string (nullable)",
      "tags": ["string"],
      "isFeatured": "boolean",
      "createdAt": "ISO 8601 timestamp",
      "publishedAt": "ISO 8601 timestamp"
    }
  ],
  "pagination": {
    "currentPage": 1,
    "totalPages": 5,
    "totalItems": 100,
    "itemsPerPage": 20
  }
}
```

**Business Rules:**
- Only return events with status "published"
- Don't return past events unless specifically requested
- Calculate `registeredCount` from active (confirmed) registrations
- Include guests in `registeredCount` (e.g., 1 registration + 2 guests = 3 count)
- Sort by date ascending by default (soonest events first)

---

#### GET `/api/events/:id`
Get detailed information for a specific event.

**Path Parameters:**
- `id`: Event ID

**Success Response (200):**
```json
{
  "success": true,
  "event": {
    "id": "string",
    "title": "string",
    "description": "string (full description)",
    "category": {
      "id": "string",
      "name": "string",
      "slug": "string",
      "color": "string"
    },
    "organizer": {
      "id": "string",
      "name": "string",
      "email": "string",
      "department": "string"
    },
    "date": "YYYY-MM-DD",
    "startTime": "HH:MM",
    "endTime": "HH:MM",
    "venue": "string",
    "location": "string",
    "capacity": "number",
    "registeredCount": "number",
    "waitlistCount": "number",
    "remainingCapacity": "number",
    "status": "published",
    "imageUrl": "string (nullable)",
    "tags": ["string"],
    "isFeatured": "boolean",
    "createdAt": "ISO 8601 timestamp",
    "publishedAt": "ISO 8601 timestamp"
  }
}
```

**Error Response (404):**
```json
{
  "success": false,
  "error": "Event not found"
}
```

**Business Rules:**
- Calculate `remainingCapacity` = capacity - registeredCount
- Only return if event is published or user is the organizer/admin

---

### 2. Categories & Venues

#### GET `/api/categories`
Get list of all active event categories.

**Success Response (200):**
```json
{
  "success": true,
  "categories": [
    {
      "id": "string",
      "name": "string",
      "slug": "string",
      "description": "string",
      "color": "string",
      "icon": "string",
      "isActive": true
    }
  ]
}
```

**Predefined Categories:**
1. Academic (blue)
2. Career (green)
3. Cultural (purple)
4. Sports (red)
5. Arts (pink)
6. Technology (indigo)
7. Wellness (teal)
8. Environmental (emerald)

---

#### GET `/api/venues`
Get list of all active venues.

**Success Response (200):**
```json
{
  "success": true,
  "venues": [
    {
      "id": "string",
      "name": "string",
      "building": "string",
      "capacity": "number",
      "facilities": ["string"],
      "isActive": true
    }
  ]
}
```

---

## Event Data Model

```typescript
interface Event {
  id: string;
  title: string;
  description: string;
  categoryId: string;
  organizerId: string;
  date: string;           // YYYY-MM-DD
  startTime: string;      // HH:MM (24-hour)
  endTime: string;        // HH:MM (24-hour)
  venue: string;
  location: string;
  capacity: number;       // 1-5000
  registeredCount: number;
  waitlistCount: number;
  status: 'draft' | 'pending' | 'published' | 'cancelled';
  imageUrl: string | null;
  tags: string[];
  isFeatured: boolean;
  createdAt: string;
  publishedAt: string | null;
  updatedAt: string;
  cancelledAt: string | null;
}
```

---

# Phase 3: Student Registration Flow

## Overview
Phase 3 enables students to register for events, manage guests, join waitlists, and access QR code tickets.

## API Endpoints

### 1. Registration Management

#### POST `/api/registrations`
Register user for an event.

**Headers:**
```
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "eventId": "string (required)",
  "guests": [
    {
      "name": "string (required)",
      "email": "string (required, must end with @umd.edu)"
    }
  ],
  "sessions": ["string"],  // For multi-session events (Phase 4+)
  "notificationPreference": "email | sms | both | none"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Successfully registered for event",
  "registration": {
    "id": "string",
    "userId": "string",
    "eventId": "string",
    "status": "confirmed",
    "ticketCode": "string (TKT-{timestamp}-{eventId})",
    "qrCode": "string (base64 or URL)",
    "registeredAt": "ISO 8601 timestamp",
    "checkInStatus": "not_checked_in",
    "guests": [
      {
        "name": "string",
        "email": "string"
      }
    ],
    "sessions": ["string"],
    "reminderSent": false
  }
}
```

**Error Response (409) - Already Registered:**
```json
{
  "success": false,
  "error": "You are already registered for this event"
}
```

**Error Response (409) - Event Full:**
```json
{
  "success": false,
  "error": "Event is full",
  "suggestion": "Join waitlist instead"
}
```

**Error Response (400) - Insufficient Capacity:**
```json
{
  "success": false,
  "error": "Only 1 spot(s) remaining. Please reduce number of guests or join the waitlist."
}
```

**Business Rules:**
- Maximum 2 guests per registration
- Guest emails must be @umd.edu
- Check if user already registered for this event
- Check capacity: remaining = capacity - registeredCount
- Count guests toward capacity (registration + guests = total attendance)
- If full, return error suggesting waitlist
- Generate unique ticket code: TKT-{timestamp}-{eventId}
- Generate QR code containing ticket code
- Send confirmation email/SMS based on preference

---

#### GET `/api/registrations`
Get current user's registrations.

**Headers:**
```
Authorization: Bearer {token}
```

**Query Parameters:**
```
status?: 'confirmed' | 'cancelled' | 'all'  // Default: 'confirmed'
include_past?: boolean                       // Default: false
```

**Success Response (200):**
```json
{
  "success": true,
  "registrations": [
    {
      "id": "string",
      "userId": "string",
      "eventId": "string",
      "event": {
        "id": "string",
        "title": "string",
        "date": "YYYY-MM-DD",
        "startTime": "HH:MM",
        "endTime": "HH:MM",
        "venue": "string",
        "organizer": {
          "name": "string"
        }
      },
      "status": "confirmed",
      "ticketCode": "string",
      "qrCode": "string",
      "registeredAt": "ISO 8601 timestamp",
      "checkInStatus": "not_checked_in | checked_in",
      "checkedInAt": "ISO 8601 timestamp (nullable)",
      "guests": [
        {
          "name": "string",
          "email": "string"
        }
      ],
      "cancelledAt": "ISO 8601 timestamp (nullable)"
    }
  ]
}
```

---

#### DELETE `/api/registrations/:id`
Cancel a registration.

**Headers:**
```
Authorization: Bearer {token}
```

**Path Parameters:**
- `id`: Registration ID

**Success Response (200):**
```json
{
  "success": true,
  "message": "Registration cancelled successfully"
}
```

**Error Response (404):**
```json
{
  "success": false,
  "error": "Registration not found"
}
```

**Error Response (400) - Already Cancelled:**
```json
{
  "success": false,
  "error": "Registration is already cancelled"
}
```

**Business Rules:**
- Can only cancel own registration
- Mark as cancelled (don't delete)
- Decrease event's registeredCount by (1 + number of guests)
- Automatically promote first person from waitlist if waitlist exists
- Send cancellation confirmation

---

### 2. Waitlist Management

#### POST `/api/waitlist`
Join waitlist for a full event.

**Headers:**
```
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "eventId": "string (required)",
  "notificationPreference": "email | sms | both"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Added to waitlist at position 5",
  "waitlistEntry": {
    "id": "string",
    "userId": "string",
    "eventId": "string",
    "position": 5,
    "joinedAt": "ISO 8601 timestamp",
    "notificationPreference": "email | sms | both"
  }
}
```

**Error Response (409) - Already on Waitlist:**
```json
{
  "success": false,
  "error": "You are already on the waitlist for this event"
}
```

**Business Rules:**
- Can only join waitlist if event is full
- Position is auto-assigned based on join order (FIFO)
- Notify user of their position

---

#### GET `/api/waitlist`
Get current user's waitlist entries.

**Headers:**
```
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "success": true,
  "waitlist": [
    {
      "id": "string",
      "userId": "string",
      "eventId": "string",
      "event": {
        "id": "string",
        "title": "string",
        "date": "YYYY-MM-DD",
        "capacity": 100,
        "registeredCount": 100
      },
      "position": 3,
      "joinedAt": "ISO 8601 timestamp",
      "notificationPreference": "email"
    }
  ]
}
```

---

#### DELETE `/api/waitlist/:id`
Leave waitlist.

**Headers:**
```
Authorization: Bearer {token}
```

**Path Parameters:**
- `id`: Waitlist entry ID

**Success Response (200):**
```json
{
  "success": true,
  "message": "Removed from waitlist successfully"
}
```

**Business Rules:**
- Can only remove own waitlist entry
- Update positions for remaining waitlist members
- Decrease event's waitlistCount

---

### 3. Waitlist Promotion (Internal)

#### POST `/api/waitlist/promote`
Automatically promote first person when spot opens.

**Internal Trigger:** Called automatically when:
- A registration is cancelled
- Capacity is increased

**Process:**
1. Get first person in waitlist (lowest position number)
2. Create registration for them
3. Remove from waitlist
4. Update positions for remaining waitlist
5. Send promotion notification (email/SMS)

---

## Registration Data Model

```typescript
interface Registration {
  id: string;
  userId: string;
  eventId: string;
  status: 'confirmed' | 'cancelled';
  ticketCode: string;        // TKT-{timestamp}-{eventId}
  qrCode: string;            // Base64 or URL to QR code image
  registeredAt: string;      // ISO 8601 timestamp
  checkInStatus: 'not_checked_in' | 'checked_in';
  checkedInAt: string | null;
  guests: Guest[];
  sessions: string[];        // For multi-session events
  reminderSent: boolean;
  cancelledAt: string | null;
}

interface Guest {
  name: string;
  email: string;           // Must end with @umd.edu
}

interface WaitlistEntry {
  id: string;
  userId: string;
  eventId: string;
  position: number;
  joinedAt: string;
  notificationPreference: 'email' | 'sms' | 'both';
}
```

---

# Phase 4: Organizer Event Management

## Overview
Phase 4 provides organizers with tools to create, manage, edit, and track their events and attendees.

## API Endpoints

### 1. Event Creation & Management

#### POST `/api/organizer/events`
Create a new event (requires organizer role).

**Headers:**
```
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "title": "string (required, max 200 chars)",
  "description": "string (required, min 50 chars)",
  "categoryId": "string (required)",
  "date": "YYYY-MM-DD (required, must be future date)",
  "startTime": "HH:MM (required)",
  "endTime": "HH:MM (required, must be after startTime)",
  "venue": "string (required)",
  "location": "string (required)",
  "capacity": "number (required, 1-5000)",
  "imageUrl": "string (optional)",
  "tags": ["string"]
}
```

**Success Response (201):**
```json
{
  "success": true,
  "message": "Event created successfully. Awaiting admin approval.",
  "event": {
    "id": "string",
    "title": "string",
    "description": "string",
    "categoryId": "string",
    "organizerId": "string",
    "date": "YYYY-MM-DD",
    "startTime": "HH:MM",
    "endTime": "HH:MM",
    "venue": "string",
    "location": "string",
    "capacity": 100,
    "registeredCount": 0,
    "waitlistCount": 0,
    "status": "pending",
    "imageUrl": "string",
    "tags": ["string"],
    "isFeatured": false,
    "createdAt": "ISO 8601 timestamp"
  }
}
```

**Business Rules:**
- New events start with status "pending" (require admin approval)
- Date must be in the future
- End time must be after start time
- Capacity between 1 and 5000
- Description minimum 50 characters
- Only approved categories allowed

---

#### GET `/api/organizer/events`
Get all events created by the organizer.

**Headers:**
```
Authorization: Bearer {token}
```

**Query Parameters:**
```
status?: 'all' | 'draft' | 'pending' | 'published' | 'cancelled'  // Default: 'all'
```

**Success Response (200):**
```json
{
  "success": true,
  "events": [
    {
      "id": "string",
      "title": "string",
      "date": "YYYY-MM-DD",
      "startTime": "HH:MM",
      "venue": "string",
      "capacity": 100,
      "registeredCount": 45,
      "waitlistCount": 3,
      "status": "published",
      "createdAt": "ISO 8601 timestamp",
      "publishedAt": "ISO 8601 timestamp"
    }
  ],
  "statistics": {
    "total": 10,
    "draft": 2,
    "pending": 3,
    "published": 4,
    "cancelled": 1
  }
}
```

---

#### PUT `/api/organizer/events/:id`
Update an event with complete event data.

**Headers:**
```
Authorization: Bearer {token}
```

**Path Parameters:**
- `id`: Event ID

**Request Body:** (All fields required except status, imageUrl, and tags)
```json
{
  "title": "string (5-200 chars)",
  "description": "string (min 50 chars)",
  "categoryId": "string (required)",
  "date": "YYYY-MM-DD (required, must be in future)",
  "startTime": "HH:MM (required, 24-hour format)",
  "endTime": "HH:MM (required, must be after startTime)",
  "venue": "string (2-200 chars)",
  "location": "string (5-500 chars)",
  "capacity": "number (1-5000, cannot be less than registered count)",
  "imageUrl": "string (optional, max 500 chars)",
  "tags": ["string"] (optional),
  "status": "string (optional: 'draft', 'pending', 'published', 'cancelled')"
}
```

**Example Request:**
```json
{
  "title": "Updated AI Workshop",
  "description": "Join us for an updated hands-on workshop covering the latest in artificial intelligence and machine learning. Perfect for students interested in AI!",
  "categoryId": "550e8400-e29b-41d4-a716-446655440003",
  "date": "2025-12-15",
  "startTime": "14:00",
  "endTime": "17:00",
  "venue": "Student Union Building",
  "location": "Room 305, 3rd Floor",
  "capacity": 120,
  "imageUrl": "https://example.com/ai-workshop.jpg",
  "tags": ["workshop", "ai", "machine-learning", "tech"],
  "status": "pending"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Event updated successfully",
  "event": {
    "id": "ad432c44-a5bb-4a98-89d6-c87d1d8b2cd4",
    "title": "Updated AI Workshop",
    "description": "Join us for an updated hands-on workshop...",
    "categoryId": "550e8400-e29b-41d4-a716-446655440003",
    "organizerId": "9db2afab-cad5-4c5d-bd7d-47a3b7edf680",
    "date": "2025-12-15",
    "startTime": "14:00",
    "endTime": "17:00",
    "venue": "Student Union Building",
    "location": "Room 305, 3rd Floor",
    "capacity": 120,
    "registeredCount": 85,
    "waitlistCount": 0,
    "remainingCapacity": 35,
    "status": "published",
    "imageUrl": "https://example.com/ai-workshop.jpg",
    "tags": ["workshop", "ai", "machine-learning", "tech"],
    "isFeatured": false,
    "createdAt": "2025-11-15T10:30:00Z",
    "updatedAt": "2025-11-30T14:25:00Z",
    "publishedAt": "2025-11-16T09:00:00Z",
    "category": {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "name": "Technology",
      "slug": "technology",
      "color": "#3B82F6"
    },
    "organizer": {
      "id": "9db2afab-cad5-4c5d-bd7d-47a3b7edf680",
      "name": "Sarah Johnson",
      "email": "organizer@umd.edu",
      "department": "Computer Science"
    }
  }
}
```

**Validation Rules:**
- All fields are required (except status, imageUrl, tags)
- Date must be in YYYY-MM-DD format and in the future
- Start/end times must be in HH:MM format (24-hour)
- End time must be after start time
- Capacity cannot be reduced below current registered count
- Category must exist and be active
- Title: 5-200 characters
- Description: minimum 50 characters
- Venue: 2-200 characters
- Location: 5-500 characters
- Capacity: 1-5000

**Status Update Rules:**
- `status` field is optional (if not provided, status remains unchanged)
- Organizers can set status to: `draft` or `pending`
- Only admins can set status to: `published`
- Cannot set status to `cancelled` via update (use cancel endpoint)
- Valid status values: `draft`, `pending`, `published`, `cancelled`

**Business Rules:**
- Can only update own events (or admin can update any)
- Cannot update cancelled events
- Organizer must be approved
- All validations from event creation apply

---

#### POST `/api/organizer/events/:id/cancel`
Cancel an event.

**Headers:**
```
Authorization: Bearer {token}
```

**Path Parameters:**
- `id`: Event ID

**Success Response (200):**
```json
{
  "success": true,
  "message": "Event cancelled successfully. All attendees have been notified."
}
```

**Business Rules:**
- Can only cancel own published events
- Cannot cancel past events
- Automatically notify all registered attendees
- Refund/cancellation logic if needed
- Status changes to "cancelled"

---

#### POST `/api/organizer/events/:id/duplicate`
Duplicate an existing event.

**Headers:**
```
Authorization: Bearer {token}
```

**Path Parameters:**
- `id`: Event ID

**Success Response (201):**
```json
{
  "success": true,
  "message": "Event duplicated successfully",
  "event": {
    // New event object with "(Copy)" appended to title
    "title": "Original Event Title (Copy)",
    "status": "draft",
    "registeredCount": 0,
    // ... other fields copied
  }
}
```

**Business Rules:**
- Can only duplicate own events
- New event created with status "draft"
- Title appended with "(Copy)"
- Date/time fields cleared (must be set manually)
- registeredCount and waitlistCount reset to 0

---

### 2. Attendee Management

#### GET `/api/organizer/events/:id/attendees`
Get list of attendees for an event.

**Headers:**
```
Authorization: Bearer {token}
```

**Path Parameters:**
- `id`: Event ID

**Query Parameters:**
```
search?: string          // Search by name or email
checkInStatus?: 'all' | 'checked_in' | 'not_checked_in'
```

**Success Response (200):**
```json
{
  "success": true,
  "attendees": [
    {
      "id": "string",
      "registrationId": "string",
      "name": "string",
      "email": "string",
      "registeredAt": "ISO 8601 timestamp",
      "checkInStatus": "checked_in | not_checked_in",
      "checkedInAt": "ISO 8601 timestamp (nullable)",
      "guests": [
        {
          "name": "string",
          "email": "string"
        }
      ]
    }
  ],
  "statistics": {
    "totalRegistrations": 45,
    "checkedIn": 32,
    "notCheckedIn": 13,
    "totalAttendees": 58,
    "capacityUsed": "45%"
  }
}
```

**Business Rules:**
- Can only view attendees for own events
- Include guests in list
- Calculate statistics

---

#### GET `/api/organizer/events/:id/attendees/export`
Export attendees list as CSV.

**Headers:**
```
Authorization: Bearer {token}
```

**Path Parameters:**
- `id`: Event ID

**Success Response (200):**
Returns CSV file with headers:
```
Name,Email,Registered At,Check-in Status,Guests
```

**Business Rules:**
- Can only export for own events
- Include all attendee data
- Separate guests with semicolons

---

### 3. Communication

#### POST `/api/organizer/events/:id/announcements`
Send announcement to all registered attendees.

**Headers:**
```
Authorization: Bearer {token}
```

**Path Parameters:**
- `id`: Event ID

**Request Body:**
```json
{
  "message": "string (required, max 1000 chars)",
  "subject": "string (required)",
  "sendVia": "email | sms | both"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Announcement sent successfully to 45 attendees",
  "recipientCount": 45
}
```

**Business Rules:**
- Can only send to own events
- Send to all confirmed registrations (not cancelled)
- Rate limiting: Max 10 announcements per day per organizer
- Track delivery status
- Save to audit log

---

## Organizer Statistics

#### GET `/api/organizer/statistics`
Get organizer's statistics dashboard.

**Headers:**
```
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "success": true,
  "statistics": {
    "totalEvents": 15,
    "upcomingEvents": 8,
    "totalRegistrations": 450,
    "totalAttendance": 380,
    "averageAttendanceRate": 84.4,
    "eventsByStatus": {
      "draft": 2,
      "pending": 3,
      "published": 8,
      "cancelled": 2
    }
  }
}
```

---

# Phase 5: Admin Console & Management

## Overview
Phase 5 provides comprehensive admin tools for approvals, reference data management, audit logging, and analytics.

## API Endpoints

### 1. Organizer Approvals

#### GET `/api/admin/approvals/organizers`
Get pending organizer approval requests.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Query Parameters:**
```
status?: 'pending' | 'approved' | 'rejected' | 'all'  // Default: 'pending'
```

**Success Response (200):**
```json
{
  "success": true,
  "requests": [
    {
      "id": "string",
      "userId": "string",
      "name": "string",
      "email": "string",
      "department": "string",
      "reason": "string (why they want to be an organizer)",
      "requestedAt": "ISO 8601 timestamp",
      "status": "pending",
      "reviewedBy": "string (nullable)",
      "reviewedAt": "ISO 8601 timestamp (nullable)",
      "notes": "string (nullable)"
    }
  ]
}
```

---

#### POST `/api/admin/approvals/organizers/:id/approve`
Approve an organizer request.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Path Parameters:**
- `id`: Request ID

**Request Body:**
```json
{
  "notes": "string (optional)"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Organizer approved successfully. User role has been updated."
}
```

**Business Rules:**
- Update user's role to "organizer"
- Set isApproved to true
- Send approval notification email
- Log action in audit trail

---

#### POST `/api/admin/approvals/organizers/:id/reject`
Reject an organizer request.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Path Parameters:**
- `id`: Request ID

**Request Body:**
```json
{
  "notes": "string (required - reason for rejection)"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Organizer request rejected"
}
```

**Business Rules:**
- Notes/reason required for rejection
- Send rejection notification with feedback
- Log action in audit trail

---

### 2. Event Approvals

#### GET `/api/admin/approvals/events`
Get pending event submissions.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Success Response (200):**
```json
{
  "success": true,
  "events": [
    {
      "id": "string",
      "eventId": "string",
      "title": "string",
      "description": "string",
      "category": {
        "name": "string"
      },
      "organizer": {
        "id": "string",
        "name": "string",
        "email": "string"
      },
      "date": "YYYY-MM-DD",
      "startTime": "HH:MM",
      "venue": "string",
      "capacity": 100,
      "submittedAt": "ISO 8601 timestamp",
      "status": "pending"
    }
  ]
}
```

---

#### POST `/api/admin/approvals/events/:id/approve`
Approve and publish an event.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Path Parameters:**
- `id`: Submission ID

**Request Body:**
```json
{
  "notes": "string (optional)"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Event approved and published"
}
```

**Business Rules:**
- Change event status to "published"
- Set publishedAt timestamp
- Notify organizer of approval
- Event becomes visible to students
- Log action in audit trail

---

#### POST `/api/admin/approvals/events/:id/reject`
Reject an event submission.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Path Parameters:**
- `id`: Submission ID

**Request Body:**
```json
{
  "notes": "string (required - reason for rejection)"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Event rejected"
}
```

**Business Rules:**
- Change event status to "rejected"
- Notes/reason required
- Notify organizer with feedback
- Log action in audit trail

---

### 3. Category Management

#### GET `/api/admin/categories`
Get all categories (including inactive).

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Success Response (200):**
```json
{
  "success": true,
  "categories": [
    {
      "id": "string",
      "name": "string",
      "slug": "string",
      "description": "string",
      "color": "string",
      "icon": "string",
      "isActive": true,
      "createdAt": "ISO 8601 timestamp",
      "updatedAt": "ISO 8601 timestamp"
    }
  ]
}
```

---

#### POST `/api/admin/categories`
Create a new category.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Request Body:**
```json
{
  "name": "string (required)",
  "slug": "string (optional, auto-generated from name)",
  "description": "string (optional)",
  "color": "string (required)",
  "icon": "string (optional)"
}
```

**Success Response (201):**
```json
{
  "success": true,
  "message": "Category created successfully",
  "category": {
    "id": "string",
    "name": "string",
    "slug": "string",
    "description": "string",
    "color": "string",
    "icon": "string",
    "isActive": true,
    "createdAt": "ISO 8601 timestamp"
  }
}
```

**Business Rules:**
- Slug must be unique
- Auto-generate slug from name if not provided
- Log action in audit trail

---

#### PUT `/api/admin/categories/:id`
Update a category.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Path Parameters:**
- `id`: Category ID

**Request Body:** (All fields optional)
```json
{
  "name": "string",
  "description": "string",
  "color": "string",
  "icon": "string"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Category updated successfully",
  "category": {
    // Updated category object
  }
}
```

---

#### DELETE `/api/admin/categories/:id`
Retire/reactivate a category (soft delete).

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Path Parameters:**
- `id`: Category ID

**Success Response (200):**
```json
{
  "success": true,
  "message": "Category retired successfully"
}
```

**Business Rules:**
- Soft delete - toggle isActive flag
- Don't actually delete (data preservation)
- Cannot retire if events are using it
- Log action in audit trail

---

### 4. Venue Management

#### GET `/api/admin/venues`
Get all venues.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Success Response (200):**
```json
{
  "success": true,
  "venues": [
    {
      "id": "string",
      "name": "string",
      "building": "string",
      "capacity": 150,
      "facilities": ["Projector", "WiFi", "Microphone"],
      "isActive": true,
      "createdAt": "ISO 8601 timestamp",
      "updatedAt": "ISO 8601 timestamp"
    }
  ]
}
```

---

#### POST `/api/admin/venues`
Create a new venue.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Request Body:**
```json
{
  "name": "string (required)",
  "building": "string (required)",
  "capacity": "number (optional)",
  "facilities": ["string"]
}
```

**Success Response (201):**
```json
{
  "success": true,
  "message": "Venue created successfully",
  "venue": {
    "id": "string",
    "name": "string",
    "building": "string",
    "capacity": 150,
    "facilities": ["string"],
    "isActive": true,
    "createdAt": "ISO 8601 timestamp"
  }
}
```

---

#### PUT `/api/admin/venues/:id`
Update a venue.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Path Parameters:**
- `id`: Venue ID

**Request Body:** (All fields optional)
```json
{
  "name": "string",
  "building": "string",
  "capacity": "number",
  "facilities": ["string"]
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Venue updated successfully",
  "venue": {
    // Updated venue object
  }
}
```

---

#### DELETE `/api/admin/venues/:id`
Retire/reactivate a venue.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Path Parameters:**
- `id`: Venue ID

**Success Response (200):**
```json
{
  "success": true,
  "message": "Venue retired successfully"
}
```

---

### 5. Audit Logs

#### GET `/api/admin/audit-logs`
Get audit log entries (read-only).

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Query Parameters:**
```
action?: string              // Filter by action type
startDate?: string           // ISO 8601 date
endDate?: string             // ISO 8601 date
userId?: string              // Filter by user
search?: string              // Search in details
page?: number                // Pagination
limit?: number               // Items per page
```

**Success Response (200):**
```json
{
  "success": true,
  "logs": [
    {
      "id": "string",
      "timestamp": "ISO 8601 timestamp",
      "action": "USER_LOGIN | ORGANIZER_APPROVED | EVENT_CREATED | etc.",
      "actor": {
        "id": "string",
        "name": "string",
        "role": "string"
      },
      "target": {
        "type": "user | event | category | venue",
        "id": "string",
        "name": "string"
      },
      "details": "string (human-readable description)",
      "ipAddress": "string",
      "userAgent": "string"
    }
  ],
  "pagination": {
    "currentPage": 1,
    "totalPages": 10,
    "totalItems": 200
  }
}
```

**Audit Action Types:**
- USER_LOGIN
- USER_LOGOUT
- ORGANIZER_APPROVED
- ORGANIZER_REJECTED
- EVENT_CREATED
- EVENT_APPROVED
- EVENT_REJECTED
- EVENT_UPDATED
- EVENT_CANCELLED
- CATEGORY_CREATED
- CATEGORY_UPDATED
- CATEGORY_RETIRED
- VENUE_CREATED
- VENUE_UPDATED
- VENUE_RETIRED
- REGISTRATION_CREATED
- REGISTRATION_CANCELLED

**Business Rules:**
- Append-only (cannot edit or delete)
- Must log all sensitive actions
- Include IP address and user agent
- Retention period (e.g., 2 years)

---

#### GET `/api/admin/audit-logs/export`
Export audit logs as CSV.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Query Parameters:** (Same as GET /api/admin/audit-logs)

**Success Response (200):**
Returns CSV file with all audit log entries.

---

### 6. Analytics & Metrics

#### GET `/api/admin/analytics`
Get system-wide analytics.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Query Parameters:**
```
startDate?: string           // ISO 8601 date
endDate?: string             // ISO 8601 date
category?: string            // Filter by category
```

**Success Response (200):**
```json
{
  "success": true,
  "analytics": {
    "summary": {
      "totalEvents": 150,
      "totalRegistrations": 5420,
      "totalAttendance": 4680,
      "noShows": 740,
      "attendanceRate": 86.3,
      "activeOrganizers": 45,
      "activeStudents": 1250
    },
    "byCategory": [
      {
        "category": "Academic",
        "events": 45,
        "registrations": 1200,
        "attendance": 1050,
        "attendanceRate": 87.5
      }
    ],
    "byDate": [
      {
        "date": "2025-11-01",
        "events": 5,
        "registrations": 150,
        "attendance": 130
      }
    ],
    "topEvents": [
      {
        "id": "string",
        "title": "string",
        "registrations": 250,
        "attendance": 230,
        "attendanceRate": 92.0
      }
    ],
    "organizerStats": [
      {
        "organizerId": "string",
        "name": "string",
        "eventsCreated": 12,
        "totalRegistrations": 450,
        "averageAttendance": 85.5
      }
    ]
  }
}
```

---

#### GET `/api/admin/analytics/export`
Export analytics data as CSV.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Success Response (200):**
Returns CSV file with analytics data.

---

#### GET `/api/admin/dashboard`
Get admin dashboard statistics.

**Headers:**
```
Authorization: Bearer {token}
Role: admin
```

**Success Response (200):**
```json
{
  "success": true,
  "stats": {
    "pendingOrganizers": 5,
    "pendingEvents": 8,
    "totalPending": 13,
    "totalEvents": 150,
    "totalRegistrations": 5420,
    "totalAttendance": 4680,
    "activeOrganizers": 45,
    "activeStudents": 1250
  }
}
```

---

# Common Data Models

## Complete Data Models Reference

### User
```typescript
interface User {
  id: string;
  email: string;
  password: string;        // Hashed
  name: string;
  role: 'student' | 'organizer' | 'admin';
  isApproved: boolean;
  department?: string;
  phone?: string;
  createdAt: string;
  updatedAt: string;
}
```

### Event
```typescript
interface Event {
  id: string;
  title: string;
  description: string;
  categoryId: string;
  organizerId: string;
  date: string;            // YYYY-MM-DD
  startTime: string;       // HH:MM
  endTime: string;         // HH:MM
  venue: string;
  location: string;
  capacity: number;
  registeredCount: number;
  waitlistCount: number;
  status: 'draft' | 'pending' | 'published' | 'cancelled';
  imageUrl: string | null;
  tags: string[];
  isFeatured: boolean;
  createdAt: string;
  publishedAt: string | null;
  updatedAt: string;
  cancelledAt: string | null;
}
```

### Registration
```typescript
interface Registration {
  id: string;
  userId: string;
  eventId: string;
  status: 'confirmed' | 'cancelled';
  ticketCode: string;
  qrCode: string;
  registeredAt: string;
  checkInStatus: 'not_checked_in' | 'checked_in';
  checkedInAt: string | null;
  guests: Guest[];
  sessions: string[];
  reminderSent: boolean;
  cancelledAt: string | null;
}
```

### Waitlist Entry
```typescript
interface WaitlistEntry {
  id: string;
  userId: string;
  eventId: string;
  position: number;
  joinedAt: string;
  notificationPreference: 'email' | 'sms' | 'both';
}
```

### Category
```typescript
interface Category {
  id: string;
  name: string;
  slug: string;
  description: string;
  color: string;
  icon: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}
```

### Venue
```typescript
interface Venue {
  id: string;
  name: string;
  building: string;
  capacity: number;
  facilities: string[];
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}
```

### Audit Log
```typescript
interface AuditLog {
  id: string;
  timestamp: string;
  action: string;
  actor: {
    id: string;
    name: string;
    role: string;
  };
  target: {
    type: string;
    id: string;
    name: string;
  };
  details: string;
  ipAddress: string;
  userAgent: string;
}
```

---

# Error Handling Standards

## Standard Error Response Format

All error responses should follow this structure:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": {
    // Additional error details (optional)
  }
}
```

## HTTP Status Codes

- **200 OK** - Successful request
- **201 Created** - Resource created successfully
- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Missing or invalid authentication
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **409 Conflict** - Resource conflict (e.g., already registered)
- **422 Unprocessable Entity** - Validation failed
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error

## Error Codes

```typescript
enum ErrorCode {
  // Authentication
  INVALID_CREDENTIALS = 'INVALID_CREDENTIALS',
  ORGANIZER_NOT_APPROVED = 'ORGANIZER_NOT_APPROVED',
  INVALID_TOKEN = 'INVALID_TOKEN',
  
  // Authorization
  INSUFFICIENT_PERMISSIONS = 'INSUFFICIENT_PERMISSIONS',
  
  // Validation
  VALIDATION_FAILED = 'VALIDATION_FAILED',
  INVALID_DATE = 'INVALID_DATE',
  INVALID_CAPACITY = 'INVALID_CAPACITY',
  
  // Registration
  ALREADY_REGISTERED = 'ALREADY_REGISTERED',
  EVENT_FULL = 'EVENT_FULL',
  INSUFFICIENT_CAPACITY = 'INSUFFICIENT_CAPACITY',
  
  // Waitlist
  ALREADY_ON_WAITLIST = 'ALREADY_ON_WAITLIST',
  
  // Resources
  EVENT_NOT_FOUND = 'EVENT_NOT_FOUND',
  USER_NOT_FOUND = 'USER_NOT_FOUND',
  REGISTRATION_NOT_FOUND = 'REGISTRATION_NOT_FOUND',
  
  // Business Logic
  CANNOT_CANCEL_PAST_EVENT = 'CANNOT_CANCEL_PAST_EVENT',
  CANNOT_EDIT_CANCELLED_EVENT = 'CANNOT_EDIT_CANCELLED_EVENT',
  
  // Rate Limiting
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED'
}
```

---

# Authentication & Authorization

## JWT Token Structure

```json
{
  "userId": "string",
  "email": "string",
  "role": "student | organizer | admin",
  "iat": 1234567890,
  "exp": 1234653890
}
```

## Role-Based Access Control

### Student Permissions:
- Browse events
- Register for events
- Join waitlists
- View own registrations
- Cancel own registrations

### Organizer Permissions:
- All student permissions, plus:
- Create events
- Edit own events
- Cancel own events
- View event attendees
- Send announcements
- Export attendee lists

### Admin Permissions:
- All organizer permissions, plus:
- Approve/reject organizers
- Approve/reject events
- Manage categories
- Manage venues
- View audit logs
- View analytics

---

# Rate Limiting

Recommended rate limits:

- **Login**: 5 attempts per 15 minutes per IP
- **Registration**: 10 per hour per user
- **Announcements**: 10 per day per organizer
- **API calls**: 100 per minute per user
- **Export**: 5 per hour per user

---

# Notification System

## Notification Types

1. **Registration Confirmation** - Email/SMS
2. **Waitlist Join** - Email/SMS with position
3. **Waitlist Promotion** - Email/SMS with ticket
4. **Event Reminder** - Email/SMS (24 hours before)
5. **Event Cancellation** - Email/SMS
6. **Event Update** - Email/SMS
7. **Organizer Approval** - Email
8. **Organizer Rejection** - Email with feedback
9. **Event Approval** - Email to organizer
10. **Event Rejection** - Email with feedback
11. **Announcement** - Email/SMS from organizer

## Notification Preferences

Users can set preferences:
- Email only
- SMS only
- Email and SMS
- None (system notifications still sent)

---

# Database Indexes

Recommended indexes for performance:

```sql
-- Users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Events
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_date ON events(date);
CREATE INDEX idx_events_organizer ON events(organizerId);
CREATE INDEX idx_events_category ON events(categoryId);

-- Registrations
CREATE INDEX idx_registrations_user ON registrations(userId);
CREATE INDEX idx_registrations_event ON registrations(eventId);
CREATE INDEX idx_registrations_status ON registrations(status);

-- Waitlist
CREATE INDEX idx_waitlist_event ON waitlist(eventId);
CREATE INDEX idx_waitlist_position ON waitlist(eventId, position);

-- Audit Logs
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_actor ON audit_logs(actorId);
```

---

# Caching Strategy

Recommended caching:

- **Categories & Venues**: Cache for 1 hour (rarely change)
- **Event List**: Cache for 5 minutes, invalidate on updates
- **User Data**: Cache in JWT token
- **Analytics**: Cache for 15 minutes

---

# File Upload (Future)

If implementing file uploads for event images:

#### POST `/api/upload/image`

**Headers:**
```
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

**Request:**
- Form field: `image` (file)
- Max size: 5MB
- Allowed types: jpg, png, webp

**Response:**
```json
{
  "success": true,
  "imageUrl": "https://storage.example.com/events/12345.jpg"
}
```

---

# Webhooks (Future)

For integrating with external systems:

- Event Published
- Event Cancelled
- Registration Created
- Check-in Completed

---

# API Versioning

Use URL versioning: `/api/v1/...`

Current version: v1

---

# Testing Recommendations

1. **Unit Tests**: All service functions
2. **Integration Tests**: All API endpoints
3. **Load Tests**: Registration endpoints (high concurrency)
4. **Security Tests**: Authentication, authorization
5. **End-to-End Tests**: Complete user flows

---

# Deployment Considerations

1. **Environment Variables**:
   - DATABASE_URL
   - JWT_SECRET
   - SMTP_CONFIG
   - SMS_PROVIDER_CONFIG
   - STORAGE_CONFIG

2. **Monitoring**:
   - Request latency
   - Error rates
   - Database performance
   - Queue depth (for notifications)

3. **Backups**:
   - Daily database backups
   - Audit log backups (immutable)

---

# Summary

This document provides complete backend API specifications for all 5 phases of the TerpSpark event management system. Each endpoint includes:

- Full request/response formats
- Business rules and validation
- Error handling
- Data models
- Security considerations

The APIs are designed to support:
- **Phase 1**: Authentication (3 user roles)
- **Phase 2**: Event browsing (search, filter, sort)
- **Phase 3**: Registration (capacity, waitlist, tickets)
- **Phase 4**: Organizer tools (create, manage, communicate)
- **Phase 5**: Admin console (approvals, analytics, audit)

All endpoints follow RESTful conventions and return consistent JSON responses.