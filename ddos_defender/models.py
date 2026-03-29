"""
Database models for DDoS protection system.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)

# Create base class for models
Base = declarative_base()


class Admin(Base):
    """Admin user model."""
    
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=False)
    face_encoding = Column(Text, nullable=False)  # JSON-encoded face encoding
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "face_encoding": json.loads(self.face_encoding) if self.face_encoding else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
        }


class BlockedIP(Base):
    """Blocked IP address model."""
    
    __tablename__ = "blocked_ips"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False, index=True)  # IPv6 compatible
    reason = Column(String(500), nullable=False)
    packet_count = Column(Integer, nullable=False)
    blocked_at = Column(DateTime, default=datetime.utcnow, index=True)
    auto_unblock_at = Column(DateTime, nullable=True, index=True)
    unblocked_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "ip_address": self.ip_address,
            "reason": self.reason,
            "packet_count": self.packet_count,
            "blocked_at": self.blocked_at.isoformat() if self.blocked_at else None,
            "auto_unblock_at": self.auto_unblock_at.isoformat() if self.auto_unblock_at else None,
            "unblocked_at": self.unblocked_at.isoformat() if self.unblocked_at else None,
            "is_active": self.is_active,
        }


class Session(Base):
    """User session model."""
    
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_valid = Column(Boolean, default=True, index=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_token": self.session_token,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_valid": self.is_valid,
        }


class WhitelistIP(Base):
    """Whitelisted IP address model."""
    
    __tablename__ = "whitelist_ips"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    added_by = Column(Integer, nullable=True)  # user_id who added this IP
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "ip_address": self.ip_address,
            "description": self.description,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "added_by": self.added_by,
        }


class AttackLog(Base):
    """Attack log model for analytics."""
    
    __tablename__ = "attack_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False, index=True)
    packet_count = Column(Integer, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    action_taken = Column(String(50), nullable=False)  # 'blocked', 'monitored', 'ignored'
    metadata = Column(JSON, nullable=True)  # Additional attack details
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "ip_address": self.ip_address,
            "packet_count": self.packet_count,
            "duration_seconds": self.duration_seconds,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "action_taken": self.action_taken,
            "metadata": self.metadata,
        }


class Database:
    """Database manager."""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = create_engine(
            self.settings.database_url,
            echo=False,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False} if "sqlite" in self.settings.database_url else {}
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def init_db(self) -> None:
        """Initialize database tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database initialized")
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def close_session(self, session: Session) -> None:
        """Close database session."""
        session.close()


# Global database instance
db = Database()


def get_db() -> Database:
    """Get database instance."""
    return db