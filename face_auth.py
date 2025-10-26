import cv2
import numpy as np
import os
from data_manager import DataManager
from file_logger import logger

class FaceAuth:
    @staticmethod
    def encode_face(image_path):
        try:
            image = cv2.imread(image_path)
            if image is None:
                return None
                
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                return None
                
            x, y, w, h = faces[0]
            face_roi = gray[y:y+h, x:x+w]
            face_roi = cv2.resize(face_roi, (100, 100))
            
            encoding = face_roi.flatten().tolist()
            logger.info(f"Face encoded successfully, vector length: {len(encoding)}")
            return encoding
        except Exception as e:
            logger.error(f"Face encoding error: {str(e)}")
            return None

    @staticmethod
    def compare_faces(encoding1, encoding2, threshold=0.85):
        try:
            if encoding1 is None or encoding2 is None:
                return False
                
            if len(encoding1) != len(encoding2):
                return False
                
            vec1 = np.array(encoding1, dtype=np.float32)
            vec2 = np.array(encoding2, dtype=np.float32)
            
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return False
                
            cosine_similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            
            logger.info(f"Face comparison similarity: {cosine_similarity:.4f}")
            return cosine_similarity > threshold
        except Exception as e:
            logger.error(f"Face comparison error: {str(e)}")
            return False

    @classmethod
    def authenticate_user(cls, image_path):
        live_encoding = cls.encode_face(image_path)
        if live_encoding is None:
            logger.warning("No face detected in the provided image")
            return None

        admins = DataManager.get_admins()
        for admin in admins:
            stored_encoding = admin.get('face_encoding')
            if cls.compare_faces(live_encoding, stored_encoding):
                logger.info(f"Successful authentication for user {admin.get('user_id')}")
                return admin
                
        logger.warning("Face authentication failed - no matching admin found")
        return None