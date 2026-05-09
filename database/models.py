from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, Date, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime
from database.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    department = Column(String, nullable=True)
    role = Column(String, default="student")
    leaves_taken_this_semester = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    registered_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    embeddings = relationship("FaceEmbedding", back_populates="student")
    attendances = relationship("Attendance", back_populates="student")
    leaves = relationship("Leave", back_populates="student")

class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.student_id"))
    encoding_blob = Column(LargeBinary, nullable=False)
    
    student = relationship("Student", back_populates="embeddings")

class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.student_id"))
    date = Column(Date, nullable=False)
    check_in = Column(DateTime, default=datetime.utcnow)
    check_out = Column(DateTime, nullable=True)
    status = Column(String, default="present") # present, absent, on_leave
    confidence = Column(Float, nullable=True)
    
    student = relationship("Student", back_populates="attendances")

class Leave(Base):
    __tablename__ = "leaves"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.student_id"))
    leave_date = Column(Date, nullable=False)
    reason = Column(String, nullable=True)
    status = Column(String, default="pending") # pending, approved, rejected
    semester = Column(Integer, nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("Student", back_populates="leaves")

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False) # In production, use hashed passwords
    name = Column(String, nullable=False, default="Admin")
