from scapy.all import sniff, IP, TCP
from collections import defaultdict
import time
import threading
from config_manager import ConfigManager
from data_manager import DataManager
from ip_blocker import IPBlocker
from file_logger import logger

class TrafficAnalyzer:
    def __init__(self):
        self.config = ConfigManager()
        self.packet_counts = defaultdict(int)
        self.last_reset = time.time()
        self.whitelist = DataManager.get_whitelist()
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Traffic analyzer started")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Traffic analyzer stopped")

    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        interface = self.config.get('monitor_interface', 'eth0')
        port = self.config.get('monitor_port', 80)
        
        logger.info(f"Starting traffic monitoring on {interface}:{port}")
        
        while self.running:
            try:
                sniff(iface=interface, 
                      prn=self._process_packet,
                      filter=f"tcp port {port}",
                      store=0, 
                      timeout=1)
            except Exception as e:
                logger.error(f"Packet capture error: {str(e)}")
                time.sleep(1)

    def _process_packet(self, packet):
        if not self.running:
            return

        current_time = time.time()
        
        # Сбрасываем счетчики каждую секунду
        if current_time - self.last_reset >= 1.0:
            self._check_thresholds()
            self.packet_counts.clear()
            self.last_reset = current_time

        # Анализируем TCP пакеты на нужный порт
        if packet.haslayer(IP) and packet.haslayer(TCP):
            ip_src = packet[IP].src
            tcp_layer = packet[TCP]
            
            port = self.config.get('monitor_port', 80)
            if tcp_layer.dport == port:
                if ip_src not in self.whitelist:
                    self.packet_counts[ip_src] += 1
                    # Логируем для отладки каждые 100 пакетов
                    if self.packet_counts[ip_src] % 100 == 0:
                        logger.info(f"Packet count for {ip_src}: {self.packet_counts[ip_src]}")

    def _check_thresholds(self):
        """Проверяем превышение порога"""
        threshold = self.config.get('block_threshold', 1000)
        
        for ip, count in self.packet_counts.items():
            if count > threshold:
                logger.warning(f"🚨 DDoS detected from {ip}, packet count: {count}")
                IPBlocker.block_ip(ip, f"DDoS attack ({count} pkt/sec)")