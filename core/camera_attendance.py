import cv2
import time
import logging
import requests
import os
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from core.face_engine import load_known_faces, recognize_faces_in_frame

logger = logging.getLogger(__name__)

API_URL = "http://127.0.0.1:8000"

# --- MediaPipe Hands Setup (Tasks API for new MediaPipe versions) ---
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'hand_landmarker.task')

if not os.path.exists(MODEL_PATH):
    logger.error(f"MediaPipe model not found at {MODEL_PATH}.")
    logger.error("Please download it using: curl -sO https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task")
    exit(1)

base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=2,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)
hand_landmarker = vision.HandLandmarker.create_from_options(options)

# Legacy drawing utils still exist for drawing, but we need to pass the right format
mp_drawing = mp.solutions.drawing_utils if hasattr(mp, 'solutions') else None
mp_hands_connections = mp.solutions.hands.HAND_CONNECTIONS if hasattr(mp, 'solutions') else frozenset([
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
    (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)
])

def is_thumbs_up(hand_landmarks):
    """
    Very simple heuristic for a thumbs up gesture.
    Y-axis goes down, so a smaller Y means higher on the screen.
    """
    # Thumb tip (4) must be significantly higher than the IP joint (3)
    thumb_tip_y = hand_landmarks[4].y
    thumb_ip_y = hand_landmarks[3].y
    
    # Other fingers must be folded (tips lower than PIP joints)
    index_folded = hand_landmarks[8].y > hand_landmarks[6].y
    middle_folded = hand_landmarks[12].y > hand_landmarks[10].y
    ring_folded = hand_landmarks[16].y > hand_landmarks[14].y
    pinky_folded = hand_landmarks[20].y > hand_landmarks[18].y
    
    # Check if thumb is pointing up
    thumb_is_up = thumb_tip_y < (thumb_ip_y - 0.05) 
    
    return thumb_is_up and index_folded and middle_folded and ring_folded and pinky_folded

def run_camera(camera_index: int = 0):
    """
    Main camera loop with GUI for real-time attendance tracking with gesture confirmation.
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        logger.error(f"Cannot open camera {camera_index}.")
        return

    logger.info("Loading known faces...")
    known_encodings, known_ids = load_known_faces()
    logger.info(f"Loaded {len(known_ids)} known faces.")

    logger.info("📷 Camera started. Press 'q' to quit.")

    # Dictionary to keep track of recently marked people so we don't spam the API
    recently_marked = {}
    MARK_COOLDOWN_SECONDS = 300  # 5 minutes
    
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.warning("Failed to grab frame.")
            time.sleep(0.1)
            continue
            
        frame_count += 1
        
        # 1. Process Hands using MediaPipe Tasks API
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        hand_results = hand_landmarker.detect(mp_image)
        
        gesture_detected = False
        
        if hand_results.hand_landmarks:
            for hand_landmarks in hand_results.hand_landmarks:
                # Draw lines manually if solutions is not available
                for connection in mp_hands_connections:
                    start_idx = connection[0]
                    end_idx = connection[1]
                    start_point = (int(hand_landmarks[start_idx].x * frame.shape[1]), int(hand_landmarks[start_idx].y * frame.shape[0]))
                    end_point = (int(hand_landmarks[end_idx].x * frame.shape[1]), int(hand_landmarks[end_idx].y * frame.shape[0]))
                    cv2.line(frame, start_point, end_point, (0, 255, 0), 2)
                
                for landmark in hand_landmarks:
                    x = int(landmark.x * frame.shape[1])
                    y = int(landmark.y * frame.shape[0])
                    cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)

                if is_thumbs_up(hand_landmarks):
                    gesture_detected = True
                    cv2.putText(frame, "THUMBS UP DETECTED", (20, 40), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)
        
        # 2. Process Faces (optimize: every 3rd frame)
        if frame_count % 3 == 0:
            face_results = recognize_faces_in_frame(frame, known_encodings, known_ids)
        else:
            if 'face_results' not in locals():
                face_results = []
                
        now = time.time()
        
        for res in face_results:
            top, right, bottom, left = res['location']
            pid = res['person_id']
            conf = res['confidence']

            if res['is_unknown']:
                color = (0, 0, 255) # Red for unknown
                label = 'Unknown'
            else:
                color = (0, 255, 0) # Green for recognized
                
                # Check if marked recently
                if pid in recently_marked and (now - recently_marked[pid]) < MARK_COOLDOWN_SECONDS:
                    label = f"{pid} (Marked)"
                    color = (255, 255, 0) # Cyan/Yellowish if already marked
                else:
                    if gesture_detected:
                        # Log Attendance!
                        try:
                            response = requests.post(f"{API_URL}/attendance/check-in", json={
                                "student_id": pid,
                                "confidence": conf
                            })
                            if response.status_code in [200, 201]:
                                logger.info(f"✅ Marked attendance for {pid}")
                                recently_marked[pid] = now
                                label = f"{pid} (Success!)"
                            else:
                                logger.warning(f"Failed to mark attendance for {pid}: {response.text}")
                                label = f"{pid} (API Error)"
                        except requests.exceptions.RequestException as e:
                            logger.error(f"API Connection Error: {e}")
                            recently_marked[pid] = now - MARK_COOLDOWN_SECONDS + 10 
                            label = f"{pid} (Offline)"
                    else:
                        label = f"{pid} (Show Thumbs Up)"

            # Draw bounding box
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Draw label
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, label, (left + 6, bottom - 6), font, 0.6, (0, 0, 0), 1)

        # Show frame
        cv2.imshow('Smart Attendance - Face Recognition', frame)

        # Hit 'q' on the keyboard to quit!
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    logger.info("Camera loop stopped.")