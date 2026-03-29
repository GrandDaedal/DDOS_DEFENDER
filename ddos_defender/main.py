"""
Main application entry point for DDoS Protection System.
"""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional

from .config import get_settings
from .logging import get_logger
from .models import Database
from .traffic_analyzer import TrafficAnalyzer
from .telegram_bot import get_telegram_bot
from .ip_blocker import get_ip_blocker

logger = get_logger(__name__)


class DDoSProtectionSystem:
    """Main DDoS protection system application."""
    
    def __init__(self):
        self.settings = get_settings()
        self.db = Database()
        self.traffic_analyzer: Optional[TrafficAnalyzer] = None
        self.telegram_bot = get_telegram_bot()
        self.ip_blocker = get_ip_blocker()
        
        self.running = False
        self.tasks = []
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("DDoS Protection System initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def _initialize_database(self):
        """Initialize database."""
        try:
            self.db.init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _start_services(self):
        """Start all services."""
        # Start traffic analyzer
        self.traffic_analyzer = TrafficAnalyzer()
        traffic_task = asyncio.create_task(self.traffic_analyzer.start())
        self.tasks.append(traffic_task)
        
        # Start Telegram bot
        bot_task = asyncio.create_task(self.telegram_bot.run())
        self.tasks.append(bot_task)
        
        logger.info("All services started")
    
    async def _stop_services(self):
        """Stop all services."""
        logger.info("Stopping services...")
        
        # Stop traffic analyzer
        if self.traffic_analyzer:
            await self.traffic_analyzer.stop()
        
        # Stop Telegram bot
        await self.telegram_bot.stop()
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("All services stopped")
    
    async def _health_check(self):
        """Periodic health check."""
        while self.running:
            try:
                # Check database connection
                session = self.db.get_session()
                session.execute("SELECT 1")
                session.close()
                
                # Log system status
                if self.traffic_analyzer:
                    stats = self.traffic_analyzer.get_stats()
                    logger.info(f"System health: {stats}")
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def run(self):
        """Run the main application."""
        try:
            self.running = True
            
            # Initialize database
            await self._initialize_database()
            
            # Start services
            await self._start_services()
            
            # Start health check
            health_task = asyncio.create_task(self._health_check())
            self.tasks.append(health_task)
            
            logger.info("🚀 DDoS Protection System started successfully")
            logger.info(f"Monitoring interface: {self.settings.monitor_interface}:{self.settings.monitor_port}")
            logger.info(f"Block threshold: {self.settings.block_threshold} packets/second")
            
            # Main loop
            while self.running:
                await asyncio.sleep(1)
            
        except asyncio.CancelledError:
            logger.info("Application cancelled")
        except Exception as e:
            logger.error(f"Application error: {e}")
            raise
        finally:
            await self._stop_services()
            logger.info("DDoS Protection System stopped")
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            # Cleanup old blocked IP entries
            self.ip_blocker.cleanup_old_entries()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


@asynccontextmanager
async def lifespan():
    """Application lifespan context manager."""
    system = None
    try:
        system = DDoSProtectionSystem()
        yield system
    finally:
        if system:
            await system.cleanup()


async def main():
    """Main entry point."""
    async with lifespan() as system:
        await system.run()


if __name__ == "__main__":
    try:
        # Setup asyncio event loop
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Run the application
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)