import asyncio
import signal
import threading
from traffic_analyzer import TrafficAnalyzer
from telegram_bot import DDoSTelegramBot
from file_logger import logger

class DDoSProtectionSystem:
    def __init__(self):
        self.traffic_analyzer = TrafficAnalyzer()
        self.telegram_bot = DDoSTelegramBot()
        self.running = False

    def start(self):
        self.running = True
        self.traffic_analyzer.start()
        
        bot_thread = threading.Thread(target=self._run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        logger.info("System started")
        

        try:
            while self.running:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            self.stop()

    def _run_bot(self):
        try:
            asyncio.run(self.telegram_bot.run())
        except Exception as e:
            logger.error(f"Bot error: {str(e)}")

    def stop(self):
        self.running = False
        self.traffic_analyzer.stop()
        logger.info("System stopped")

def main():
    system = DDoSProtectionSystem()
    
    def signal_handler(signum, frame):
        system.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    system.start()

if __name__ == "__main__":
    main()