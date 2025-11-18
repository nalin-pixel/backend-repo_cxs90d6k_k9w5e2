import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import db, create_document, get_documents
from schemas import User, Event, Volunteer, EventVolunteer, Donation, Task, Attendance

app = FastAPI(title="ImpactFlow API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Security / Auth Setup =====
SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: int

class RegisterPayload(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    role: str = "volunteer"  # admin/volunteer/coordinator/donor
    password: str

class LoginPayload(BaseModel):
    email: str
    password: str

# Helpers

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def serialize_doc(doc: dict):
    if not doc:
        return doc
    doc = dict(doc)
    _id = doc.get("_id")
    if isinstance(_id, ObjectId):
        doc["id"] = str(_id)
        del doc["_id"]
    return doc

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

# ===== Auth Endpoints =====
@app.post("/auth/register", response_model=dict)
async def register(payload: RegisterPayload):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    existing = db["user"].find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_data = payload.model_dump()
    user_data["password"] = get_password_hash(user_data["password"])  # hash password
    user_data["is_active"] = True
    inserted_id = db["user"].insert_one(user_data).inserted_id
    return {"id": str(inserted_id)}

@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm expects fields: username, password; we use username as email
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    user = db["user"].find_one({"email": form_data.username})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not verify_password(form_data.password, user.get("password", "")):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="User is inactive")
    token = create_access_token({"sub": str(user["_id"]), "role": user.get("role", "volunteer")})
    return {"access_token": token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db["user"].find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_exception
    return serialize_doc(user)

@app.get("/auth/me", response_model=dict)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    # Remove password before returning
    current_user.pop("password", None)
    return current_user

# ===== Users =====
@app.post("/users", response_model=dict)
async def create_user(user: User):
    # Hash password before storing
    user_dict = user.model_dump()
    user_dict["password"] = get_password_hash(user_dict["password"]) if user_dict.get("password") else None
    user_id = db["user"].insert_one(user_dict).inserted_id
    return {"id": str(user_id)}

@app.get("/users", response_model=List[dict])
async def list_users():
    docs = get_documents("user")
    sanitized = []
    for d in docs:
        d.pop("password", None)
        sanitized.append(serialize_doc(d))
    return sanitized

# ===== Events =====
@app.post("/events", response_model=dict)
async def create_event(event: Event):
    event_id = create_document("event", event)
    return {"id": event_id}

@app.get("/events", response_model=List[dict])
async def list_events():
    docs = get_documents("event")
    return [serialize_doc(d) for d in docs]

# ===== Volunteers =====
@app.post("/volunteers", response_model=dict)
async def create_volunteer(volunteer: Volunteer):
    volunteer_id = create_document("volunteer", volunteer)
    return {"id": volunteer_id}

@app.get("/volunteers", response_model=List[dict])
async def list_volunteers():
    docs = get_documents("volunteer")
    return [serialize_doc(d) for d in docs]

# ===== Event-Volunteer mapping =====
@app.post("/event-volunteers", response_model=dict)
async def map_event_volunteer(ev: EventVolunteer):
    mapping_id = create_document("eventvolunteer", ev)
    return {"id": mapping_id}

@app.get("/event-volunteers", response_model=List[dict])
async def list_event_volunteers(event_id: Optional[str] = None):
    filt = {"event_id": event_id} if event_id else {}
    docs = get_documents("eventvolunteer", filt)
    return [serialize_doc(d) for d in docs]

# ===== Donations =====
@app.post("/donations", response_model=dict)
async def create_donation(donation: Donation):
    donation_id = create_document("donation", donation)
    return {"id": donation_id}

@app.get("/donations", response_model=List[dict])
async def list_donations(event_id: Optional[str] = None):
    filt = {"event_id": event_id} if event_id else {}
    docs = get_documents("donation", filt)
    return [serialize_doc(d) for d in docs]

# ===== Tasks =====
@app.post("/tasks", response_model=dict)
async def create_task(task: Task):
    task_id = create_document("task", task)
    return {"id": task_id}

@app.get("/tasks", response_model=List[dict])
async def list_tasks(event_id: Optional[str] = None):
    filt = {"event_id": event_id} if event_id else {}
    docs = get_documents("task", filt)
    return [serialize_doc(d) for d in docs]

# ===== Attendance =====
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
