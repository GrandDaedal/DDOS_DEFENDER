import os
import json
from file_logger import logger

class ConfigManager:
    _instance = None
    _config = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        config_path = "config/settings.json"
        try:
            with open(config_path, 'r') as f:
                self._config = json.load(f)
            for key in self._config:
                env_value = os.getenv(key.upper())
                if env_value is not None:
                    if isinstance(self._config[key], int):
                        self._config[key] = int(env_value)
                    elif isinstance(self._config[key], bool):
                        self._config[key] = env_value.lower() == 'true'
                    else:
                        self._config[key] = env_value
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            raise

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value