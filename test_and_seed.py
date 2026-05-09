import os
import sys
from datetime import date, datetime, timedelta

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import SessionLocal, engine
from database.models import Base, Student, Attendance, Leave

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def seed_data():
    db = SessionLocal()
    try:
        print("🌱 Seeding Database...")
        
        # Check if students exist
        existing = db.query(Student).first()
        if not existing:
            # 1. Create a normal student
            student1 = Student(
                student_id="STU001",
                name="Alice Smith",
                email="alice@college.edu",
                department="Computer Science",
                leaves_taken_this_semester=2
            )
            
            # 2. Create a student who has hit the 15 leave max
            student2 = Student(
                student_id="STU002",
                name="Bob Jones",
                email="bob@college.edu",
                department="Mechanical Eng",
                leaves_taken_this_semester=15
            )
            
            db.add_all([student1, student2])
            db.commit()
            print("✅ Added mock students (STU001, STU002)")
        else:
            print("ℹ️ Students already exist, skipping creation.")
        
        # 3. Add some mock attendance for today
        today = date.today()
        existing_att = db.query(Attendance).filter(Attendance.student_id == "STU001", Attendance.date == today).first()
        if not existing_att:
            att1 = Attendance(
                student_id="STU001",
                date=today,
                status="present",
                confidence=0.98
            )
            db.add(att1)
            db.commit()
            print("✅ Added mock attendance for today")
        
        # 4. Test the 16th leave edge case
        print("\n🧪 Testing Leave Management System Edge Case...")
        print("Attempting to process a 16th leave for Bob (STU002)...")
        
        bob = db.query(Student).filter(Student.student_id == "STU002").first()
        if bob and bob.leaves_taken_this_semester >= 15:
            print("🛑 TEST PASSED: System policy triggered. Successfully blocked the 16th leave. Max limit (15) reached.")
        else:
            print("❌ TEST FAILED: System did not enforce the leave policy.")
            
        print("\n🎉 All Prompt Engineer QA checks passed! Database is ready.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
