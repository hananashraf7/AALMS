from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

# --- Student Schemas ---
class StudentBase(BaseModel):
    student_id: str
    name: str
    email: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = "student"

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    id: int
    leaves_taken_this_semester: int
    is_active: bool
    registered_at: datetime

    class Config:
        from_attributes = True

# --- Leave Schemas ---
class LeaveApply(BaseModel):
    student_id: str
    leave_date: date
    reason: str
    semester: int

class LeaveResponse(BaseModel):
    id: int
    student_id: str
    leave_date: date
    reason: Optional[str]
    status: str
    semester: int
    applied_at: datetime

    class Config:
        from_attributes = True

# --- Attendance Schemas ---
class AttendanceCreate(BaseModel):
    student_id: str
    confidence: Optional[float] = None

class AttendanceResponse(BaseModel):
    id: int
    student_id: str
    date: date
    check_in: datetime
    check_out: Optional[datetime]
    status: str
    confidence: Optional[float]

    class Config:
        from_attributes = True

class FramePayload(BaseModel):
    image_base64: str

class FaceRegistrationPayload(BaseModel):
    student_id: str
    name: str
    department: str
    image_base64: str

class AttendanceOverviewResponse(BaseModel):
    student_id: str
    name: str
    total_working_days: int
    days_present: int
    leaves_taken: int
    attendance_percentage: float
    has_shortage: bool

    class Config:
        from_attributes = True

# --- Admin Schemas ---
class AdminAuthPayload(BaseModel):
    username: str
    password: str

class AdminSettingsPayload(BaseModel):
    current_username: str
    new_username: str
    new_password: str
    name: str
