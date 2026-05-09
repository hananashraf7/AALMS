import cv2
import face_recognition
import numpy as np
import logging
import pickle
import os

from database.database import SessionLocal
from database.models import Student, FaceEmbedding

logger = logging.getLogger(__name__)

def register_person_faces(student_id: str, image_paths: list):
    """
    Register person using face_recognition.
    Extracts face encodings from images and averages them for a robust single representation.
    Saves to the SQLAlchemy database.
    """
    encodings = []
    
    for img_path in image_paths:
        if not os.path.exists(img_path):
            logger.warning(f"File not found: {img_path}")
            continue
            
        img = face_recognition.load_image_file(img_path)
        
        # Detect faces
        face_locations = face_recognition.face_locations(img, model="hog")
        
        if not face_locations:
            logger.warning(f"No face detected in {img_path}")
            continue
            
        if len(face_locations) > 1:
            logger.warning(f"Multiple faces detected in {img_path}, using the largest one")
            face_locations = sorted(face_locations, key=lambda loc: (loc[2]-loc[0])*(loc[1]-loc[3]), reverse=True)
            
        encoding = face_recognition.face_encodings(img, [face_locations[0]])[0]
        encodings.append(encoding)
        logger.info(f"✅ Extracted face encoding from {img_path}")
        
    if not encodings:
        return False, f"Failed to extract face encodings for {student_id}. Please use clearer photos.", None
        
    avg_encoding = np.mean(encodings, axis=0)
    encoding_blob = pickle.dumps(avg_encoding)
    
    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            return False, f"Student {student_id} not found in database.", None
            
        existing_embedding = db.query(FaceEmbedding).filter(FaceEmbedding.student_id == student_id).first()
        if existing_embedding:
            existing_embedding.encoding_blob = encoding_blob
        else:
            new_embedding = FaceEmbedding(student_id=student_id, encoding_blob=encoding_blob)
            db.add(new_embedding)
            
        db.commit()
    finally:
        db.close()
        
    return True, f"Successfully registered face for {student_id} using {len(encodings)} images.", avg_encoding

def load_known_faces():
    """Load known faces from SQLAlchemy database."""
    db = SessionLocal()
    known_encodings = []
    known_ids = []
    
    try:
        embeddings = db.query(FaceEmbedding).all()
        for emb in embeddings:
            try:
                encoding = pickle.loads(emb.encoding_blob)
                known_encodings.append(encoding)
                known_ids.append(emb.student_id)
            except Exception as e:
                logger.error(f"Error loading encoding for {emb.student_id}: {e}")
    finally:
        db.close()

    logger.info(f"Loaded {len(known_encodings)} face encodings from database")
    return known_encodings, known_ids

def recognize_faces_in_frame(frame, known_encodings, known_ids, tolerance=0.55):
    """
    Recognize faces in a BGR frame (from webcam/base64).
    Returns list of dicts with recognition results including UNKNOWN faces
    so the frontend always draws boxes.
    
    Key fix: do NOT shrink the frame — browser frames can be small already.
    We only resize if the frame is very large (>1080p wide).
    """
    if frame is None:
        return []

    # Convert BGR to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    h, w = rgb_frame.shape[:2]
    
    # Only downscale if image is very large (keeps detail for small webcam frames)
    scale = 1.0
    if w > 960:
        scale = 960 / w
        rgb_frame = cv2.resize(rgb_frame, (int(w * scale), int(h * scale)))

    # Use HOG model — faster and more reliable on CPU/webcam
    face_locations = face_recognition.face_locations(rgb_frame, model="hog")
    
    if not face_locations:
        return []
        
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations, num_jitters=1)
    
    results = []
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        # Scale back to original frame size
        if scale != 1.0:
            top = int(top / scale)
            right = int(right / scale)
            bottom = int(bottom / scale)
            left = int(left / scale)

        best_match_id = None
        confidence = 0.0
        
        if known_encodings:
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_match_index = int(np.argmin(face_distances))
            best_dist = float(face_distances[best_match_index])
            
            # tolerance: lower distance = better match
            if best_dist <= tolerance:
                best_match_id = known_ids[best_match_index]
                confidence = max(0.0, 1.0 - best_dist)
                    
        results.append({
            'person_id': best_match_id if best_match_id else "Unknown",
            'location': (top, right, bottom, left),
            'confidence': confidence,
            'is_unknown': best_match_id is None
        })
        
    return results