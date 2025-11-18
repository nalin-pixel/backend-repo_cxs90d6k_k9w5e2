import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import User, Event, Volunteer, EventVolunteer, Donation, Task, Attendance

app = FastAPI(title="ImpactFlow API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"name": "ImpactFlow API", "status": "ok"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# Helper to convert ObjectId to string

def serialize_doc(doc: dict):
    if not doc:
        return doc
    doc = dict(doc)
    _id = doc.get("_id")
    if isinstance(_id, ObjectId):
        doc["id"] = str(_id)
        del doc["_id"]
    return doc


# Users minimal endpoints
@app.post("/users", response_model=dict)
async def create_user(user: User):
    user_id = create_document("user", user)
    return {"id": user_id}

@app.get("/users", response_model=List[dict])
async def list_users():
    docs = get_documents("user")
    return [serialize_doc(d) for d in docs]


# Events
@app.post("/events", response_model=dict)
async def create_event(event: Event):
    event_id = create_document("event", event)
    return {"id": event_id}

@app.get("/events", response_model=List[dict])
async def list_events():
    docs = get_documents("event")
    return [serialize_doc(d) for d in docs]


# Volunteers
@app.post("/volunteers", response_model=dict)
async def create_volunteer(volunteer: Volunteer):
    volunteer_id = create_document("volunteer", volunteer)
    return {"id": volunteer_id}

@app.get("/volunteers", response_model=List[dict])
async def list_volunteers():
    docs = get_documents("volunteer")
    return [serialize_doc(d) for d in docs]


# Event-Volunteer mapping
@app.post("/event-volunteers", response_model=dict)
async def map_event_volunteer(ev: EventVolunteer):
    mapping_id = create_document("eventvolunteer", ev)
    return {"id": mapping_id}

@app.get("/event-volunteers", response_model=List[dict])
async def list_event_volunteers(event_id: Optional[str] = None):
    filt = {"event_id": event_id} if event_id else {}
    docs = get_documents("eventvolunteer", filt)
    return [serialize_doc(d) for d in docs]


# Donations
@app.post("/donations", response_model=dict)
async def create_donation(donation: Donation):
    donation_id = create_document("donation", donation)
    return {"id": donation_id}

@app.get("/donations", response_model=List[dict])
async def list_donations(event_id: Optional[str] = None):
    filt = {"event_id": event_id} if event_id else {}
    docs = get_documents("donation", filt)
    return [serialize_doc(d) for d in docs]


# Tasks
@app.post("/tasks", response_model=dict)
async def create_task(task: Task):
    task_id = create_document("task", task)
    return {"id": task_id}

@app.get("/tasks", response_model=List[dict])
async def list_tasks(event_id: Optional[str] = None):
    filt = {"event_id": event_id} if event_id else {}
    docs = get_documents("task", filt)
    return [serialize_doc(d) for d in docs]


# Attendance
@app.post("/attendance", response_model=dict)
async def mark_attendance(a: Attendance):
    att_id = create_document("attendance", a)
    return {"id": att_id}

@app.get("/attendance", response_model=List[dict])
async def list_attendance(event_id: Optional[str] = None):
    filt = {"event_id": event_id} if event_id else {}
    docs = get_documents("attendance", filt)
    return [serialize_doc(d) for d in docs]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
