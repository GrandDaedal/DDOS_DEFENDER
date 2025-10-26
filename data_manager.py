import json
import threading
from file_logger import logger

class DataManager:
    _lock = threading.Lock()

    @classmethod
    def read_json(cls, filepath):
        with cls._lock:
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except FileNotFoundError:
                return []
            except Exception as e:
                logger.error(f"Error reading {filepath}: {str(e)}")
                return []

    @classmethod
    def write_json(cls, filepath, data):
        with cls._lock:
            try:
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=4)
                return True
            except Exception as e:
                logger.error(f"Error writing {filepath}: {str(e)}")
                return False

    @classmethod
    def add_admin(cls, admin_data):
        admins = cls.read_json('data/admins.json')
        admins.append(admin_data)
        return cls.write_json('data/admins.json', admins)

    @classmethod
    def remove_admin(cls, user_id):
        admins = cls.read_json('data/admins.json')
        admins = [a for a in admins if a.get('user_id') != user_id]
        return cls.write_json('data/admins.json', admins)

    @classmethod
    def get_admins(cls):
        return cls.read_json('data/admins.json')

    @classmethod
    def add_blocked_ip(cls, ip_data):
        blocked = cls.read_json('data/blocked_ips.json')
        blocked.append(ip_data)
        return cls.write_json('data/blocked_ips.json', blocked)

    @classmethod
    def remove_blocked_ip(cls, ip):
        blocked = cls.read_json('data/blocked_ips.json')
        blocked = [b for b in blocked if b.get('ip') != ip]
        return cls.write_json('data/blocked_ips.json', blocked)

    @classmethod
    def get_blocked_ips(cls):
        return cls.read_json('data/blocked_ips.json')

    @classmethod
    def get_whitelist(cls):
        return cls.read_json('data/whitelist.json')

    @classmethod
    def update_sessions(cls, sessions):
        return cls.write_json('data/sessions.json', sessions)

    @classmethod
    def get_sessions(cls):
        return cls.read_json('data/sessions.json')