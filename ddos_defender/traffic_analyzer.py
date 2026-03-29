"""
Advanced traffic analyzer with sliding window rate limiting.
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, List, Set, Optional, Tuple
import threading
from scapy.all import sniff, IP, TCP, UDP
from scapy.sendrecv import AsyncSniffer

from .config import get_settings
from .logging import get_logger
from .models import Database, WhitelistIP, AttackLog
from .ip_blocker import IPBlocker

logger = get_logger(__name__)


class SlidingWindowCounter:
    """Sliding window counter for rate limiting."""
    
    def __init__(self, window_size: int = 10):
        """
        Initialize sliding window counter.
        
        Args:
            window_size: Window size in seconds
        """
        self.window_size = window_size
        self.windows: Dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()
    
    def add_event(self, key: str, timestamp: float = None) -> None:
        """
        Add an event for a key.
        
        Args:
            key: Key to track (e.g., IP address)
            timestamp: Event timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            window = self.windows[key]
            window.append(timestamp)
            
            # Remove old events outside the window
            cutoff = timestamp - self.window_size
            while window and window[0] < cutoff:
                window.popleft()
    
    def get_count(self, key: str) -> int:
        """
        Get event count for a key within the window.
        
        Args:
            key: Key to get count for
            
        Returns:
            Event count within the window
        """
        with self.lock:
            window = self.windows.get(key, deque())
            return len(window)
    
    def get_rate(self, key: str) -> float:
        """
        Get event rate for a key (events per second).
        
        Args:
            key: Key to get rate for
            
        Returns:
            Events per second
        """
        count = self.get_count(key)
        return count / self.window_size if self.window_size > 0 else 0
    
    def cleanup_old_keys(self, max_age: int = 3600) -> None:
        """
        Clean up old keys that haven't been used.
        
        Args:
            max_age: Maximum age in seconds to keep keys
        """
        cutoff = time.time() - max_age
        with self.lock:
            keys_to_remove = []
            for key, window in self.windows.items():
                if not window or window[-1] < cutoff:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.windows[key]


class TrafficAnalyzer:
    """Advanced traffic analyzer with sliding window rate limiting."""
    
    def __init__(self):
        self.settings = get_settings()
        self.db = Database()
        self.ip_blocker = IPBlocker()
        
        # Rate limiting
        self.rate_counter = SlidingWindowCounter(self.settings.rate_window_seconds)
        
        # Whitelist cache
        self.whitelist: Set[str] = set()
        self.whitelist_updated = 0
        
        # Statistics
        self.total_packets = 0
        self.blocked_attacks = 0
        self.detected_attacks = 0
        
        # Async sniffer
        self.sniffer: Optional[AsyncSniffer] = None
        self.running = False
        
        # Worker queue
        self.packet_queue = asyncio.Queue(maxsize=self.settings.max_queue_size)
        
        logger.info(f"Traffic analyzer initialized with window size: {self.settings.rate_window_seconds}s")
    
    def _load_whitelist(self) -> None:
        """Load whitelist from database."""
        try:
            session = self.db.get_session()
            whitelist_ips = session.query(WhitelistIP).all()
            
            new_whitelist = {ip.ip_address for ip in whitelist_ips}
            if new_whitelist != self.whitelist:
                self.whitelist = new_whitelist
                self.whitelist_updated = time.time()
                logger.info(f"Loaded {len(self.whitelist)} whitelisted IPs")
            
            session.close()
            
        except Exception as e:
            logger.error(f"Failed to load whitelist: {e}")
    
    def _is_whitelisted(self, ip: str) -> bool:
        """
        Check if IP is whitelisted.
        
        Args:
            ip: IP address to check
            
        Returns:
            True if whitelisted, False otherwise
        """
        # Refresh whitelist every 5 minutes
        if time.time() - self.whitelist_updated > 300:
            self._load_whitelist()
        
        return ip in self.whitelist
    
    def _process_packet(self, packet) -> None:
        """
        Process a single packet.
        
        Args:
            packet: Scapy packet
        """
        if not self.running:
            return
        
        self.total_packets += 1
        
        # Extract IP and port information
        if packet.haslayer(IP):
            ip_src = packet[IP].src
            
            # Skip whitelisted IPs
            if self._is_whitelisted(ip_src):
                return
            
            # Check if it's targeting our monitored port
            target_port = None
            if packet.haslayer(TCP):
                target_port = packet[TCP].dport
            elif packet.haslayer(UDP):
                target_port = packet[UDP].dport
            
            if target_port == self.settings.monitor_port:
                # Add to rate counter
                self.rate_counter.add_event(ip_src)
                
                # Check rate
                rate = self.rate_counter.get_rate(ip_src)
                
                # Log high rates for monitoring
                if rate > self.settings.block_threshold * 0.5:  # 50% of threshold
                    logger.debug(f"High traffic from {ip_src}: {rate:.1f} pkt/s")
                
                # Check if threshold exceeded
                if rate > self.settings.block_threshold:
                    self.detected_attacks += 1
                    logger.warning(f"🚨 DDoS detected from {ip_src}: {rate:.1f} pkt/s")
                    
                    # Block the IP
                    self.ip_blocker.block_ip(
                        ip_src,
                        f"DDoS attack ({rate:.1f} pkt/s, threshold: {self.settings.block_threshold})"
                    )
                    self.blocked_attacks += 1
                    
                    # Log attack for analytics
                    self._log_attack(ip_src, rate)
    
    def _log_attack(self, ip: str, rate: float) -> None:
        """
        Log attack for analytics.
        
        Args:
            ip: Attacker IP
            rate: Attack rate in packets per second
        """
        try:
            session = self.db.get_session()
            
            attack_log = AttackLog(
                ip_address=ip,
                packet_count=int(rate * self.settings.rate_window_seconds),
                duration_seconds=self.settings.rate_window_seconds,
                action_taken="blocked",
                metadata={
                    "rate": rate,
                    "threshold": self.settings.block_threshold,
                    "timestamp": time.time()
                }
            )
            
            session.add(attack_log)
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Failed to log attack: {e}")
    
    async def _packet_worker(self, worker_id: int) -> None:
        """
        Worker coroutine for processing packets.
        
        Args:
            worker_id: Worker ID for logging
        """
        logger.info(f"Packet worker {worker_id} started")
        
        while self.running:
            try:
                packet = await asyncio.wait_for(
                    self.packet_queue.get(),
                    timeout=1.0
                )
                
                self._process_packet(packet)
                self.packet_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Packet worker {worker_id} error: {e}")
    
    def _packet_callback(self, packet) -> None:
        """
        Callback for packet capture.
        
        Args:
            packet: Captured packet
        """
        if self.running:
            try:
                # Try to put packet in queue (non-blocking)
                self.packet_queue.put_nowait(packet)
            except asyncio.QueueFull:
                logger.warning("Packet queue full, dropping packet")
    
    async def start(self) -> None:
        """Start traffic analyzer."""
        if self.running:
            logger.warning("Traffic analyzer already running")
            return
        
        self.running = True
        
        # Load whitelist
        self._load_whitelist()
        
        # Start packet workers
        worker_tasks = []
        for i in range(self.settings.worker_count):
            task = asyncio.create_task(self._packet_worker(i))
            worker_tasks.append(task)
        
        # Start packet capture
        filter_str = f"tcp port {self.settings.monitor_port} or udp port {self.settings.monitor_port}"
        
        self.sniffer = AsyncSniffer(
            iface=self.settings.monitor_interface,
            filter=filter_str,
            prn=self._packet_callback,
            store=False
        )
        
        self.sniffer.start()
        
        logger.info(f"Traffic analyzer started on {self.settings.monitor_interface}:{self.settings.monitor_port}")
        logger.info(f"Using {self.settings.worker_count} workers with {self.settings.rate_window_seconds}s window")
        
        # Main loop
        try:
            while self.running:
                # Clean up old rate counter keys every minute
                self.rate_counter.cleanup_old_keys()
                
                # Log statistics every 30 seconds
                if self.total_packets > 0 and int(time.time()) % 30 == 0:
                    logger.info(
                        f"Stats: {self.total_packets} packets, "
                        f"{self.detected_attacks} attacks detected, "
                        f"{self.blocked_attacks} blocked"
                    )
                
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("Traffic analyzer cancelled")
        except Exception as e:
            logger.error(f"Traffic analyzer error: {e}")
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop traffic analyzer."""
        if not self.running:
            return
        
        self.running = False
        
        # Stop packet capture
        if self.sniffer:
            self.sniffer.stop()
            self.sniffer = None
        
        # Wait for queue to empty
        await self.packet_queue.join()
        
        logger.info("Traffic analyzer stopped")
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get analyzer statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_packets": self.total_packets,
            "detected_attacks": self.detected_attacks,
            "blocked_attacks": self.blocked_attacks,
            "queue_size": self.packet_queue.qsize(),
            "whitelist_size": len(self.whitelist),
            "active_tracked_ips": len(self.rate_counter.windows),
        }