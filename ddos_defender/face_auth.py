"""
Advanced face recognition using deep learning.
"""

import os
import json
import tempfile
import numpy as np
from typing import Optional, Dict, Any, List
import cv2
import face_recognition
from datetime import datetime

from .config import get_settings
from .logging import get_logger
from .models import Admin, Database

logger = get_logger(__name__)


class FaceAuthenticator:
    """Advanced face authenticator using deep learning."""
    
    def __init__(self):
        self.settings = get_settings()
        self.db = Database()
        self.known_faces: List[np.ndarray] = []
        self.known_admin_ids: List[int] = []
        self._load_known_faces()
    
    def _load_known_faces(self) -> None:
        """Load known faces from database."""
        try:
            session = self.db.get_session()
            admins = session.query(Admin).filter(Admin.is_active == True).all()
            
            self.known_faces.clear()
            self.known_admin_ids.clear()
            
            for admin in admins:
                try:
                    encoding = json.loads(admin.face_encoding)
                    face_array = np.array(encoding, dtype=np.float64)
                    self.known_faces.append(face_array)
                    self.known_admin_ids.append(admin.user_id)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Failed to load face encoding for admin {admin.user_id}: {e}")
            
            logger.info(f"Loaded {len(self.known_faces)} known faces from database")
            session.close()
            
        except Exception as e:
            logger.error(f"Failed to load known faces: {e}")
    
    def encode_face(self, image_path: str) -> Optional[List[float]]:
        """
        Encode a face from an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Face encoding as list of floats or None if no face found
        """
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Find face locations
            face_locations = face_recognition.face_locations(image, model="hog")
            
            if not face_locations:
                logger.warning("No face found in image")
                return None
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if not face_encodings:
                logger.warning("Could not encode face")
                return None
            
            # Use the first face found
            encoding = face_encodings[0].tolist()
            logger.info(f"Face encoded successfully, vector length: {len(encoding)}")
            return encoding
            
        except Exception as e:
            logger.error(f"Face encoding error: {e}")
            return None
    
    def authenticate(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user from a face image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Admin dictionary if authenticated, None otherwise
        """
        try:
            # Encode the face from the image
            live_encoding = self.encode_face(image_path)
            if live_encoding is None:
                return None
            
            live_array = np.array(live_encoding, dtype=np.float64)
            
            # Compare with known faces
            if not self.known_faces:
                logger.warning("No known faces in database")
                return None
            
            # Calculate face distances
            face_distances = face_recognition.face_distance(self.known_faces, live_array)
            
            # Find the best match
            best_match_index = np.argmin(face_distances)
            best_distance = face_distances[best_match_index]
            
            # Convert distance to similarity (0-1 scale, higher is more similar)
            similarity = 1.0 - best_distance
            
            logger.info(f"Best match similarity: {similarity:.4f}, threshold: {self.settings.face_similarity_threshold}")
            
            # Check if similarity meets threshold
            if similarity >= self.settings.face_similarity_threshold:
                admin_id = self.known_admin_ids[best_match_index]
                
                # Get admin details from database
                session = self.db.get_session()
                admin = session.query(Admin).filter(Admin.user_id == admin_id).first()
                session.close()
                
                if admin:
                    logger.info(f"Successful authentication for user {admin.user_id}")
                    return admin.to_dict()
            
            logger.warning(f"Authentication failed - similarity {similarity:.4f} below threshold")
            return None
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def verify_face_quality(self, image_path: str) -> Dict[str, Any]:
        """
        Verify face image quality before processing.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with quality metrics
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return {"valid": False, "error": "Could not read image"}
            
            height, width = image.shape[:2]
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Load face cascade
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            # Detect faces
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                return {"valid": False, "error": "No face detected"}
            
            if len(faces) > 1:
                return {"valid": False, "error": "Multiple faces detected"}
            
            x, y, w, h = faces[0]
            
            # Calculate face metrics
            face_area = w * h
            image_area = width * height
            face_ratio = face_area / image_area
            
            # Check if face is too small
            if face_ratio < 0.1:  # Face should be at least 10% of image
                return {"valid": False, "error": "Face too small in image"}
            
            # Check if face is centered
            center_x = x + w / 2
            center_y = y + h / 2
            image_center_x = width / 2
            image_center_y = height / 2
            
            offset_x = abs(center_x - image_center_x) / width
            offset_y = abs(center_y - image_center_y) / height
            
            if offset_x > 0.3 or offset_y > 0.3:
                return {"valid": False, "error": "Face not centered"}
            
            # Calculate brightness
            face_roi = gray[y:y+h, x:x+w]
            brightness = np.mean(face_roi)
            
            if brightness < 50 or brightness > 200:
                return {"valid": False, "error": "Poor lighting conditions"}
            
            # Calculate sharpness (Laplacian variance)
            sharpness = cv2.Laplacian(face_roi, cv2.CV_64F).var()
            
            if sharpness < 100:
                return {"valid": False, "error": "Image is blurry"}
            
            return {
                "valid": True,
                "face_count": len(faces),
                "face_ratio": face_ratio,
                "brightness": brightness,
                "sharpness": sharpness,
                "offset_x": offset_x,
                "offset_y": offset_y,
            }
            
        except Exception as e:
            logger.error(f"Face quality verification error: {e}")
            return {"valid": False, "error": str(e)}
    
    def add_admin_face(self, user_id: int, username: str, image_path: str) -> bool:
        """
        Add a new admin face to the database.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            image_path: Path to face image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify image quality
            quality = self.verify_face_quality(image_path)
            if not quality["valid"]:
                logger.error(f"Image quality check failed: {quality.get('error')}")
                return False
            
            # Encode face
            encoding = self.encode_face(image_path)
            if encoding is None:
                logger.error("Failed to encode face")
                return False
            
            # Check if admin already exists
            session = self.db.get_session()
            existing_admin = session.query(Admin).filter(Admin.user_id == user_id).first()
            
            if existing_admin:
                # Update existing admin
                existing_admin.username = username
                existing_admin.face_encoding = json.dumps(encoding)
                existing_admin.is_active = True
            else:
                # Create new admin
                admin = Admin(
                    user_id=user_id,
                    username=username,
                    face_encoding=json.dumps(encoding),
                    is_active=True
                )
                session.add(admin)
            
            session.commit()
            session.close()
            
            # Reload known faces
            self._load_known_faces()
            
            logger.info(f"Admin {user_id} ({username}) added/updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add admin face: {e}")
            return False


# Global authenticator instance
authenticator = FaceAuthenticator()


def get_authenticator() -> FaceAuthenticator:
    """Get face authenticator instance."""
    return authenticator