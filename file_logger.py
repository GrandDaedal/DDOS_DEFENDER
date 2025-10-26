import logging
from logging.handlers import TimedRotatingFileHandler
import os
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName
        }
        return json.dumps(log_entry)

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('ddos_logger')
    logger.setLevel(logging.INFO)
    
    handler = TimedRotatingFileHandler(
        'logs/app.log',
        when='D',
        interval=1,
        backupCount=7
    )
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    return logger

logger = setup_logger()