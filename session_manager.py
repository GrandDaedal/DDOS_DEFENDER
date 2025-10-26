import time
from data_manager import DataManager
from config_manager import ConfigManager
from file_logger import logger

class SessionManager:
    @staticmethod
    def create_session(user_id):
        sessions = DataManager.get_sessions()
        sessions = [s for s in sessions if s.get('user_id') != user_id]
        new_session = {
            'user_id': user_id,
            'session_start': time.time(),
            'last_activity': time.time()
        }
        sessions.append(new_session)
        DataManager.update_sessions(sessions)
        logger.info(f"Session created for user {user_id}")

    @staticmethod
    def validate_session(user_id):
        sessions = DataManager.get_sessions()
        for session in sessions:
            if session.get('user_id') == user_id:
                timeout = ConfigManager().get('session_timeout_minutes') * 60
                if time.time() - session.get('last_activity') < timeout:
                    session['last_activity'] = time.time()
                    DataManager.update_sessions(sessions)
                    return True
        return False

    @staticmethod
    def remove_session(user_id):
        sessions = DataManager.get_sessions()
        sessions = [s for s in sessions if s.get('user_id') != user_id]
        DataManager.update_sessions(sessions)
        logger.info(f"Session removed for user {user_id}")