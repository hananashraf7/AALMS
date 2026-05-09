import cv2
import face_recognition
import numpy as np
import pickle
import time
import os
import sys

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import SessionLocal, engine
from database.models import Base, Student, FaceEmbedding

# Ensure tables exist
Base.metadata.create_all(bind=engine)

STUDENTS_TO_REGISTER = [
    {"student_id": "230812", "name": "Azra Rashid", "department": "Student"},
    {"student_id": "230841", "name": "Munazim Ashraf", "department": "Student"},
    {"student_id": "240884", "name": "Wasiq", "department": "Student"},
    {"student_id": "231013", "name": "Hanan Ashraf", "department": "Student"},
]

def register_students():
    db = SessionLocal()
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    try:
        for student_data in STUDENTS_TO_REGISTER:
            # 1. Ensure student exists in DB
            student = db.query(Student).filter(Student.student_id == student_data["student_id"]).first()
            if not student:
                student = Student(
                    student_id=student_data["student_id"],
                    name=student_data["name"],
                    department=student_data["department"]
                )
                db.add(student)
                db.commit()
            
            # Check if embedding already exists
            existing_emb = db.query(FaceEmbedding).filter(FaceEmbedding.student_id == student_data["student_id"]).first()
            if existing_emb:
                print(f"✅ {student_data['name']} ({student_data['student_id']}) is already registered with a face. Skipping...")
                continue
                
            print(f"\n--- REGISTERING {student_data['name']} ({student_data['student_id']}) ---")
            print("Please look at the camera. Press 'c' to capture, or 's' to skip this person.")
            
            captured = False
            while not captured:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # Draw instructions
                display_frame = frame.copy()
                cv2.putText(display_frame, f"Registering: {student_data['name']}", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(display_frame, "Press 'c' to capture face, 's' to skip", (20, 80), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Detect face to show bounding box just as feedback
                rgb_small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)[:, :, ::-1]
                face_locs = face_recognition.face_locations(rgb_small)
                for (top, right, bottom, left) in face_locs:
                    cv2.rectangle(display_frame, (left*4, top*4), (right*4, bottom*4), (255, 0, 0), 2)
                    
                cv2.imshow("Face Registration", display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('s'):
                    print(f"Skipping {student_data['name']}")
                    break
                elif key == ord('c'):
                    if not face_locs:
                        print("❌ No face detected. Try again.")
                        continue
                    if len(face_locs) > 1:
                        print("❌ Multiple faces detected. Please ensure only one person is in frame.")
                        continue
                        
                    print("📸 Capturing and extracting embedding...")
                    # Extract encoding
                    rgb_frame = frame[:, :, ::-1]
                    face_encodings = face_recognition.face_encodings(rgb_frame, [(top*4, right*4, bottom*4, left*4)])
                    
                    if face_encodings:
                        encoding = face_encodings[0]
                        encoding_blob = pickle.dumps(encoding)
                        
                        # Save to DB
                        new_embedding = FaceEmbedding(student_id=student_data["student_id"], encoding_blob=encoding_blob)
                        db.add(new_embedding)
                        db.commit()
                        
                        print(f"✅ Successfully registered face for {student_data['name']}!")
                        captured = True
                        time.sleep(1) # Pause to let user read success
                    else:
                        print("❌ Failed to extract encoding. Try again.")
                        
    finally:
        cap.release()
        cv2.destroyAllWindows()
        db.close()
        
    print("\n🎉 Registration session completed!")

if __name__ == "__main__":
    register_students()
