"""
Structured logging configuration.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger

from .config import get_settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Add log level
        log_record["level"] = record.levelname
        
        # Add module and function info
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        
        # Add process and thread info
        log_record["process"] = record.process
        log_record["thread"] = record.thread
        
        # Remove default fields we don't need
        log_record.pop("message", None)
        log_record.pop("asctime", None)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level = record.levelname
        module = record.module
        function = record.funcName
        message = record.getMessage()
        
        return f"{timestamp} | {level:8} | {module}.{function} | {message}"


def setup_logging() -> logging.Logger:
    """Setup structured logging."""
    settings = get_settings()
    
    # Create logger
    logger = logging.getLogger("ddos_defender")
    logger.setLevel(getattr(logging, settings.log_level))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter based on configuration
    if settings.log_format.lower() == "json":
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(module)s %(function)s %(message)s"
        )
    else:
        formatter = TextFormatter()
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler for JSON logs
    try:
        file_handler = logging.FileHandler("logs/app.log")
        file_handler.setFormatter(CustomJsonFormatter())
        logger.addHandler(file_handler)
    except (FileNotFoundError, PermissionError):
        logger.warning("Could not create file handler for logs/app.log")
    
    # Create error file handler
    try:
        error_handler = logging.FileHandler("logs/error.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(CustomJsonFormatter())
        logger.addHandler(error_handler)
    except (FileNotFoundError, PermissionError):
        logger.warning("Could not create error file handler")
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


# Global logger instance
logger = setup_logging()


def get_logger(name: str = "ddos_defender") -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)