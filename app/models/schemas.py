"""
Pydantic schemas - define the shape of data going in/out of the API.
Keeping these separate from the SQLAlchemy models (models.py) is a deliberate
pattern: it lets the API contract evolve independently of the DB schema.
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


# ---------- Users ----------
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "student"
    student_id: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    student_id: Optional[str] = None
    has_face_registered: bool = False

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Face Registration ----------
class FaceRegisterRequest(BaseModel):
    image_base64: str  # data URL or raw base64 string from webcam capture


# ---------- Class Sessions ----------
class ClassSessionCreate(BaseModel):
    name: str
    start_time: datetime
    end_time: datetime


class ClassSessionOut(BaseModel):
    id: int
    name: str
    start_time: datetime
    end_time: datetime
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Attendance ----------
class CheckInRequest(BaseModel):
    session_id: int
    image_base64: Optional[str] = None   # for face check-in
    qr_token: Optional[str] = None       # for QR fallback check-in


class AttendanceOut(BaseModel):
    id: int
    user_id: int
    session_id: int
    timestamp: datetime
    method: str
    confidence_score: Optional[float] = None
    status: str
    is_anomaly: bool
    anomaly_reason: Optional[str] = None

    class Config:
        from_attributes = True


class AttendanceWithUser(AttendanceOut):
    user_name: str
    student_id: Optional[str] = None


# ---------- Analytics ----------
class AttendanceSummary(BaseModel):
    user_id: int
    user_name: str
    total_sessions: int
    present_count: int
    late_count: int
    absent_count: int
    attendance_percentage: float
