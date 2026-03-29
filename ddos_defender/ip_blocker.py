"""
Advanced IP blocker with Redis integration and better error handling.
"""

import asyncio
import time
import subprocess
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import redis
from redis.exceptions import RedisError

from .config import get_settings
from .logging import get_logger
from .models import Database, BlockedIP
from .telegram_bot import TelegramBot

logger = get_logger(__name__)


class RedisManager:
    """Redis manager for distributed blocking."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self) -> None:
        """Connect to Redis."""
        try:
            self.client = redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                password=self.settings.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {self.settings.redis_host}:{self.settings.redis_port}")
            
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if self.client is None:
            return False
        
        try:
            self.client.ping()
            return True
        except RedisError:
            return False
    
    def block_ip(self, ip: str, ttl: int) -> bool:
        """
        Block IP in Redis.
        
        Args:
            ip: IP address to block
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            key = f"blocked:{ip}"
            self.client.setex(key, ttl, "blocked")
            logger.debug(f"IP {ip} blocked in Redis for {ttl}s")
            return True
        except RedisError as e:
            logger.error(f"Failed to block IP {ip} in Redis: {e}")
            return False
    
    def is_blocked(self, ip: str) -> bool:
        """
        Check if IP is blocked in Redis.
        
        Args:
            ip: IP address to check
            
        Returns:
            True if blocked, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            key = f"blocked:{ip}"
            return self.client.exists(key) > 0
        except RedisError as e:
            logger.error(f"Failed to check IP {ip} in Redis: {e}")
            return False
    
    def unblock_ip(self, ip: str) -> bool:
        """
        Unblock IP in Redis.
        
        Args:
            ip: IP address to unblock
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            key = f"blocked:{ip}"
            self.client.delete(key)
            logger.debug(f"IP {ip} unblocked in Redis")
            return True
        except RedisError as e:
            logger.error(f"Failed to unblock IP {ip} in Redis: {e}")
            return False


class IPBlocker:
    """Advanced IP blocker with Redis integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.db = Database()
        self.redis = RedisManager()
        self.telegram_bot: Optional[TelegramBot] = None
        self._blocked_cache: Dict[str, float] = {}
        self._cache_lock = threading.Lock()
        
        logger.info("IP blocker initialized")
    
    def set_telegram_bot(self, bot: TelegramBot) -> None:
        """Set Telegram bot instance for notifications."""
        self.telegram_bot = bot
    
    def _execute_iptables(self, command: List[str]) -> bool:
        """
        Execute iptables command.
        
        Args:
            command: iptables command as list
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                ["sudo"] + command,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                logger.error(f"iptables command failed: {result.stderr}")
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("iptables command timed out")
            return False
        except Exception as e:
            logger.error(f"iptables command error: {e}")
            return False
    
    def block_ip(self, ip: str, reason: str) -> bool:
        """
        Block an IP address.
        
        Args:
            ip: IP address to block
            reason: Reason for blocking
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if already blocked
            if self.is_blocked(ip):
                logger.warning(f"IP {ip} is already blocked")
                return True
            
            # Block in iptables
            iptables_commands = [
                ["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"],
                ["iptables", "-A", "FORWARD", "-s", ip, "-j", "DROP"]
            ]
            
            success = True
            for cmd in iptables_commands:
                if not self._execute_iptables(cmd):
                    success = False
                    break
            
            if not success:
                logger.error(f"Failed to block IP {ip} in iptables")
                return False
            
            # Block in Redis
            ttl = self.settings.auto_unblock_minutes * 60
            self.redis.block_ip(ip, ttl)
            
            # Update cache
            with self._cache_lock:
                self._blocked_cache[ip] = time.time()
            
            # Save to database
            session = self.db.get_session()
            
            blocked_ip = BlockedIP(
                ip_address=ip,
                reason=reason,
                packet_count=0,  # Will be updated by traffic analyzer
                blocked_at=datetime.utcnow(),
                auto_unblock_at=datetime.utcnow() + timedelta(minutes=self.settings.auto_unblock_minutes),
                is_active=True
            )
            
            session.add(blocked_ip)
            session.commit()
            session.close()
            
            logger.warning(f"Blocked IP: {ip}, reason: {reason}")
            
            # Schedule automatic unblock
            self._schedule_unblock(ip)
            
            # Send notification
            asyncio.create_task(self._send_notification(ip, reason))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to block IP {ip}: {e}")
            return False
    
    def unblock_ip(self, ip: str) -> bool:
        """
        Unblock an IP address.
        
        Args:
            ip: IP address to unblock
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Unblock in iptables
            iptables_commands = [
                ["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"],
                ["iptables", "-D", "FORWARD", "-s", ip, "-j", "DROP"]
            ]
            
            success = True
            for cmd in iptables_commands:
                if not self._execute_iptables(cmd):
                    # Command might fail if rule doesn't exist, which is OK
                    logger.debug(f"iptables rule not found for {ip}")
            
            # Unblock in Redis
            self.redis.unblock_ip(ip)
            
            # Update cache
            with self._cache_lock:
                if ip in self._blocked_cache:
                    del self._blocked_cache[ip]
            
            # Update database
            session = self.db.get_session()
            
            blocked_ip = session.query(BlockedIP).filter(
                BlockedIP.ip_address == ip,
                BlockedIP.is_active == True
            ).first()
            
            if blocked_ip:
                blocked_ip.is_active = False
                blocked_ip.unblocked_at = datetime.utcnow()
                session.commit()
            
            session.close()
            
            logger.info(f"Unblocked IP: {ip}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unblock IP {ip}: {e}")
            return False
    
    def is_blocked(self, ip: str) -> bool:
        """
        Check if IP is blocked.
        
        Args:
            ip: IP address to check
            
        Returns:
            True if blocked, False otherwise
        """
        # Check cache first
        with self._cache_lock:
            if ip in self._blocked_cache:
                # Check if cache entry is still valid (5 minute cache)
                if time.time() - self._blocked_cache[ip] < 300:
                    return True
        
        # Check Redis
        if self.redis.is_blocked(ip):
            with self._cache_lock:
                self._blocked_cache[ip] = time.time()
            return True
        
        # Check database
        try:
            session = self.db.get_session()
            blocked = session.query(BlockedIP).filter(
                BlockedIP.ip_address == ip,
                BlockedIP.is_active == True
            ).first() is not None
            session.close()
            
            if blocked:
                with self._cache_lock:
                    self._blocked_cache[ip] = time.time()
            
            return blocked
            
        except Exception as e:
            logger.error(f"Failed to check if IP {ip} is blocked: {e}")
            return False
    
    def _schedule_unblock(self, ip: str) -> None:
        """Schedule automatic unblocking of IP."""
        def unblock_after_delay():
            time.sleep(self.settings.auto_unblock_minutes * 60)
            self.unblock_ip(ip)
            logger.info(f"Auto-unblocked IP: {ip}")
        
        thread = threading.Thread(target=unblock_after_delay, daemon=True)
        thread.start()
    
    async def _send_notification(self, ip: str, reason: str) -> None:
        """Send notification about blocked IP."""
        if not self.telegram_bot:
            return
        
        try:
            message = (
                f"🚨 **DDoS Attack Blocked**\n\n"
                f"• **IP Address:** `{ip}`\n"
                f"• **Reason:** {reason}\n"
                f"• **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"• **Auto-unblock:** {self.settings.auto_unblock_minutes} minutes\n\n"
                f"Use `/unblock {ip}` to unblock manually."
            )
            
            await self.telegram_bot.send_admin_message(message)
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def get_blocked_ips(self) -> List[Dict[str, Any]]:
        """
        Get list of currently blocked IPs.
        
        Returns:
            List of blocked IP dictionaries
        """
        try:
            session = self.db.get_session()
            blocked_ips = session.query(BlockedIP).filter(
                BlockedIP.is_active == True
            ).order_by(BlockedIP.blocked_at.desc()).all()
            
            result = [ip.to_dict() for ip in blocked_ips]
            session.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get blocked IPs: {e}")
            return []
    
    def cleanup_old_entries(self) -> None:
        """Clean up old blocked IP entries from database."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=7)
            
            session = self.db.get_session()
            old_entries = session.query(BlockedIP).filter(
                BlockedIP.blocked_at < cutoff,
                BlockedIP.is_active == False
            ).all()
            
            for entry in old_entries:
                session.delete(entry)
            
            session.commit()
            session.close()
            
            logger.info(f"Cleaned up {len(old_entries)} old blocked IP entries")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old entries: {e}")


# Global IP blocker instance
ip_blocker = IPBlocker()


def get_ip_blocker() -> IPBlocker:
    """Get IP blocker instance."""
    return ip_blocker