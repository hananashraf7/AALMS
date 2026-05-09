from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from database import models
from database.database import engine, get_db
from api import schemas
import base64
import numpy as np
import cv2
import pickle
import face_recognition
import time
from core.face_engine import recognize_faces_in_frame, load_known_faces

# Cache for face encodings to speed up frame processing
KNOWN_ENCODINGS = []
KNOWN_IDS = []
LAST_LOAD_TIME = 0

def get_cached_faces():
    global KNOWN_ENCODINGS, KNOWN_IDS, LAST_LOAD_TIME
    # Reload every 30 seconds or if explicitly invalidated
    if time.time() - LAST_LOAD_TIME > 30 or LAST_LOAD_TIME == 0:
        KNOWN_ENCODINGS, KNOWN_IDS = load_known_faces()
        LAST_LOAD_TIME = time.time()
    return KNOWN_ENCODINGS, KNOWN_IDS

def force_cache_reload():
    """Immediately reload face encodings from DB (call after registration)."""
    global KNOWN_ENCODINGS, KNOWN_IDS, LAST_LOAD_TIME
    KNOWN_ENCODINGS, KNOWN_IDS = load_known_faces()
    LAST_LOAD_TIME = time.time()
    return len(KNOWN_ENCODINGS)

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Attendance System API")

# Seed default admin if missing
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    admin = db.query(models.Admin).first()
    if not admin:
        default_admin = models.Admin(username="hananashraf", password="coldspot", name="Hanan Ashraf")
        db.add(default_admin)
        db.commit()

# Configure CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Smart Attendance API"}

# --- Student Endpoints ---
@app.post("/students/", response_model=schemas.StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    db_student = db.query(models.Student).filter(models.Student.student_id == student.student_id).first()
    if db_student:
        raise HTTPException(status_code=400, detail="Student ID already registered")
    
    new_student = models.Student(**student.model_dump())
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student

@app.get("/students/", response_model=List[schemas.StudentResponse])
def get_students(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Student).offset(skip).limit(limit).all()

# --- Leave Management Endpoints ---
@app.post("/leaves/apply/", response_model=schemas.LeaveResponse)
def apply_for_leave(leave: schemas.LeaveApply, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.student_id == leave.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    if student.leaves_taken_this_semester >= 15:
        raise HTTPException(status_code=400, detail="Maximum leaves (15) already taken this semester")

    # Check if leave already exists for this date
    existing_leave = db.query(models.Leave).filter(
        models.Leave.student_id == leave.student_id,
        models.Leave.leave_date == leave.leave_date
    ).first()
    if existing_leave:
        raise HTTPException(status_code=400, detail="Leave already applied for this date")

    # Create leave (pending by default)
    new_leave = models.Leave(**leave.model_dump(), status="pending")
    
    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)
    return new_leave

@app.post("/leaves/{leave_id}/approve")
def approve_leave(leave_id: int, db: Session = Depends(get_db)):
    leave = db.query(models.Leave).filter(models.Leave.id == leave_id).first()
    if not leave or leave.status != "pending":
        raise HTTPException(status_code=400, detail="Invalid leave or already processed")
        
    student = db.query(models.Student).filter(models.Student.student_id == leave.student_id).first()
    if student.leaves_taken_this_semester >= 15:
        raise HTTPException(status_code=400, detail="Student has already reached max leaves (15)")
        
    leave.status = "approved"
    student.leaves_taken_this_semester += 1
    db.commit()
    return {"message": "Leave approved"}

@app.post("/leaves/{leave_id}/reject")
def reject_leave(leave_id: int, db: Session = Depends(get_db)):
    leave = db.query(models.Leave).filter(models.Leave.id == leave_id).first()
    if not leave or leave.status != "pending":
        raise HTTPException(status_code=400, detail="Invalid leave or already processed")
        
    leave.status = "rejected"
    db.commit()
    return {"message": "Leave rejected"}

@app.get("/leaves/all", response_model=List[schemas.LeaveResponse])
def get_all_leaves(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    return db.query(models.Leave).order_by(models.Leave.applied_at.desc()).offset(skip).limit(limit).all()

@app.get("/leaves/{student_id}", response_model=List[schemas.LeaveResponse])
def get_student_leaves(student_id: str, db: Session = Depends(get_db)):
    return db.query(models.Leave).filter(models.Leave.student_id == student_id).all()

# --- Attendance View Endpoints ---
@app.post("/attendance/check-in", response_model=schemas.AttendanceResponse)
def check_in(attendance: schemas.AttendanceCreate, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.student_id == attendance.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    today = date.today()
    existing = db.query(models.Attendance).filter(
        models.Attendance.student_id == attendance.student_id,
        models.Attendance.date == today
    ).first()
    
    if existing:
        # Already checked in
        return existing
        
    new_attendance = models.Attendance(
        student_id=attendance.student_id,
        date=today,
        confidence=attendance.confidence,
        status="present"
    )
    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)
    return new_attendance

@app.get("/attendance/today", response_model=List[schemas.AttendanceResponse])
def get_today_attendance(db: Session = Depends(get_db)):
    today = date.today()
    return db.query(models.Attendance).filter(models.Attendance.date == today).all()

@app.get("/attendance/overview", response_model=List[schemas.AttendanceOverviewResponse])
def get_attendance_overview(db: Session = Depends(get_db)):
    from sqlalchemy import func
    
    # Calculate total working days (unique dates in attendance table)
    total_working_days = db.query(func.count(func.distinct(models.Attendance.date))).scalar() or 0
    
    students = db.query(models.Student).all()
    overview = []
    
    for student in students:
        # Count days present
        days_present = db.query(models.Attendance).filter(
            models.Attendance.student_id == student.student_id,
            models.Attendance.status == "present"
        ).count()
        
        # Calculate percentage
        if total_working_days == 0:
            percentage = 100.0 # Default if no days recorded yet
        else:
            percentage = (days_present / total_working_days) * 100.0
            
        has_shortage = percentage < 75.0
        
        overview.append({
            "student_id": student.student_id,
            "name": student.name,
            "total_working_days": total_working_days,
            "days_present": days_present,
            "leaves_taken": student.leaves_taken_this_semester,
            "attendance_percentage": round(percentage, 1),
            "has_shortage": has_shortage
        })
        
    return overview

@app.get("/attendance/all", response_model=List[schemas.AttendanceResponse])
def get_all_attendance(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    return db.query(models.Attendance).order_by(models.Attendance.date.desc(), models.Attendance.check_in.desc()).offset(skip).limit(limit).all()

# --- Web Camera Endpoints ---
def decode_base64_image(base64_string: str):
    # Remove header if present (e.g., "data:image/jpeg;base64,")
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    image_data = base64.b64decode(base64_string)
    np_arr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return img

@app.post("/students/register_with_face")
def register_student_with_face(payload: schemas.FaceRegistrationPayload, db: Session = Depends(get_db)):
    # 1. Check if student exists
    db_student = db.query(models.Student).filter(models.Student.student_id == payload.student_id).first()
    if not db_student:
        new_student = models.Student(
            student_id=payload.student_id,
            name=payload.name,
            department=payload.department
        )
        db.add(new_student)
        db.commit()
        db.refresh(new_student)
    
    # 2. Extract encoding from base64 image
    img = decode_base64_image(payload.image_base64)
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Use HOG model (consistent with recognition engine)
    face_locations = face_recognition.face_locations(rgb_img, model="hog")
    if not face_locations:
        raise HTTPException(status_code=400, detail="No face detected in the image. Ensure good lighting and face the camera directly.")
    if len(face_locations) > 1:
        raise HTTPException(status_code=400, detail="Multiple faces detected. Please ensure only one person is in frame.")
        
    encoding = face_recognition.face_encodings(rgb_img, face_locations, num_jitters=2)[0]
    encoding_blob = pickle.dumps(encoding)
    
    # 3. Save to DB
    existing_embedding = db.query(models.FaceEmbedding).filter(models.FaceEmbedding.student_id == payload.student_id).first()
    if existing_embedding:
        existing_embedding.encoding_blob = encoding_blob
    else:
        new_embedding = models.FaceEmbedding(student_id=payload.student_id, encoding_blob=encoding_blob)
        db.add(new_embedding)
    
    db.commit()
    
    # Immediately force cache reload so this face is recognized right away
    count = force_cache_reload()
    
    return {"message": f"Successfully registered face for {payload.name}", "total_known_faces": count}

@app.get("/cache/reload")
def reload_face_cache():
    """Manually trigger face encoding cache reload. Call this after registration."""
    count = force_cache_reload()
    return {"message": "Cache reloaded", "known_faces": count}

@app.post("/attendance/process_frame")
def process_camera_frame(payload: schemas.FramePayload, db: Session = Depends(get_db)):
    img = decode_base64_image(payload.image_base64)
    
    # Get cached known faces
    encodings, ids = get_cached_faces()
    
    # Always run face detection — return boxes even for unknown faces
    results = recognize_faces_in_frame(img, encodings, ids)
    if not results:
        return {"results": []}
    
    # Automatically log attendance for recognized faces
    today = date.today()
    for res in results:
        if not res['is_unknown']:
            pid = res['person_id']
            conf = res['confidence']
            
            # Check if already marked today
            existing = db.query(models.Attendance).filter(
                models.Attendance.student_id == pid,
                models.Attendance.date == today
            ).first()
            
            if not existing:
                new_attendance = models.Attendance(
                    student_id=pid,
                    date=today,
                    confidence=conf,
                    status="present"
                )
                db.add(new_attendance)
                db.commit()
                res['marked_just_now'] = True
            else:
                res['marked_just_now'] = False
                res['already_marked'] = True
                
    return {"results": results}

# --- Admin Endpoints ---
@app.post("/admin/login")
def admin_login(payload: schemas.AdminAuthPayload, db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(
        models.Admin.username == payload.username,
        models.Admin.password == payload.password
    ).first()
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"message": "Success", "name": admin.name, "username": admin.username}

@app.post("/admin/settings")
def update_admin_settings(payload: schemas.AdminSettingsPayload, db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.username == payload.current_username).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
        
    # Check if new username is already taken by another admin
    if payload.new_username != payload.current_username:
        exists = db.query(models.Admin).filter(models.Admin.username == payload.new_username).first()
        if exists:
            raise HTTPException(status_code=400, detail="Username already taken")
            
    admin.username = payload.new_username
    admin.password = payload.new_password
    admin.name = payload.name
    db.commit()
    return {"message": "Settings updated successfully", "name": admin.name, "username": admin.username}

# --- Calendar / Reset Endpoints ---
@app.get("/attendance/calendar")
def get_attendance_calendar(db: Session = Depends(get_db)):
    """Returns attendance grouped by date for calendar view."""
    from sqlalchemy import func
    students = db.query(models.Student).all()
    all_records = db.query(models.Attendance).order_by(models.Attendance.date.desc()).all()
    
    # Group by date
    calendar: dict = {}
    for rec in all_records:
        day = str(rec.date)
        if day not in calendar:
            calendar[day] = []
        calendar[day].append({
            "student_id": rec.student_id,
            "check_in": rec.check_in.strftime("%H:%M") if rec.check_in else None,
            "status": rec.status,
            "confidence": round(rec.confidence * 100, 1) if rec.confidence else None
        })
    
    return {"calendar": calendar, "total_students": len(students)}

@app.get("/attendance/debug")
def debug_face_db(db: Session = Depends(get_db)):
    """Check how many face embeddings are stored."""
    embeddings = db.query(models.FaceEmbedding).all()
    students = db.query(models.Student).all()
    encodings, ids = get_cached_faces()
    return {
        "stored_embeddings": len(embeddings),
        "registered_students": len(students),
        "cached_faces": len(encodings),
        "cached_ids": ids,
        "embedding_details": [{"student_id": e.student_id, "size": len(e.encoding_blob)} for e in embeddings]
    }

@app.delete("/attendance/reset-today")
def reset_today_attendance(db: Session = Depends(get_db)):
    """Admin: Delete all attendance records for today."""
    today = date.today()
    deleted = db.query(models.Attendance).filter(models.Attendance.date == today).delete()
    db.commit()
    return {"message": f"Deleted {deleted} attendance records for today ({today})"}
