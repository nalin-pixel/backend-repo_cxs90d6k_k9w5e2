"""
Database Schemas for ImpactFlow

Each Pydantic model corresponds to a MongoDB collection. Collection name is the
lowercased class name.

Examples:
- User -> "user"
- Event -> "event"
- Donation -> "donation"
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# Core Users
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    role: str = Field("volunteer", description="Role: admin/volunteer/coordinator/donor")
    password: str = Field(..., description="Password (store hashed in production)")
    is_active: bool = Field(True, description="Active status")

# Events
class Event(BaseModel):
    event_title: str = Field(..., description="Title of the event")
    date: str = Field(..., description="ISO date string e.g., 2025-05-20")
    location: str = Field(..., description="Event location")
    description: Optional[str] = Field(None, description="Event description")
    budget: Optional[float] = Field(0, ge=0, description="Budget in currency units")
    status: str = Field("upcoming", description="upcoming/ongoing/completed/cancelled")
    banner_url: Optional[str] = Field(None, description="Public URL to banner image")

# Volunteers (profile separate from User when role is volunteer)
class Volunteer(BaseModel):
    name: str
    skills: List[str] = []
    availability: Optional[str] = None
    phone: Optional[str] = None

# Mapping between Events and Volunteers
class EventVolunteer(BaseModel):
    event_id: str
    volunteer_id: str
    role: Optional[str] = Field(None, description="Assigned role in the event")

# Donations
class Donation(BaseModel):
    donor_name: str
    event_id: Optional[str] = Field(None, description="Linked event id")
    amount: Optional[float] = Field(None, ge=0, description="Amount for cash donation")
    kind: str = Field("cash", description="cash/material")
    material_desc: Optional[str] = Field(None, description="Description if material donation")
    date: str = Field(..., description="ISO date string")

# Tasks
class Task(BaseModel):
    event_id: str
    task_name: str
    assigned_to: Optional[str] = Field(None, description="Volunteer id")
    status: str = Field("Pending", description="Pending/In Progress/Done")

# Attendance
class Attendance(BaseModel):
    event_id: str
    volunteer_id: str
    method: str = Field("manual", description="manual/qr/otp")
    timestamp: Optional[datetime] = None
