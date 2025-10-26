import subprocess
import time
import threading
from data_manager import DataManager
from config_manager import ConfigManager
from file_logger import logger
import asyncio

class IPBlocker:
    _blocked_ips = {}
    _bot_instance = None

    @classmethod
    def set_bot(cls, bot_instance):
        cls._bot_instance = bot_instance

    @classmethod
    def block_ip(cls, ip, reason):
        try:
            # Блокируем IP в iptables
            subprocess.run(["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"], check=True)
            timestamp = time.time()
            
            # Записываем в базу данных
            DataManager.add_blocked_ip({
                "ip": ip,
                "timestamp": timestamp,
                "reason": reason
            })
            cls._blocked_ips[ip] = timestamp
            
            logger.warning(f"Blocked IP: {ip}, reason: {reason}")
            
            # Отправляем уведомление администратору
            if cls._bot_instance:
                asyncio.create_task(cls._send_alert(ip, reason))
            
            # Запускаем автоматическую разблокировку
            cls._schedule_unblock(ip)
            
        except Exception as e:
            logger.error(f"Failed to block IP {ip}: {str(e)}")

    @classmethod
    def unblock_ip(cls, ip):
        try:
            # Разблокируем IP в iptables
            subprocess.run(["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"], check=True)
            DataManager.remove_blocked_ip(ip)
            
            if ip in cls._blocked_ips:
                del cls._blocked_ips[ip]
                
            logger.info(f"Unblocked IP: {ip}")
            
        except Exception as e:
            logger.error(f"Failed to unblock IP {ip}: {str(e)}")

    @classmethod
    def _schedule_unblock(cls, ip):
        def unblock_after_delay():
            unblock_minutes = ConfigManager().get('auto_unblock_minutes', 60)
            time.sleep(unblock_minutes * 60)
            cls.unblock_ip(ip)

        threading.Thread(target=unblock_after_delay, daemon=True).start()

    @classmethod
    async def _send_alert(cls, ip, reason):
        try:
            if cls._bot_instance:
                message = (
                    f"🚨 **Обнаружена DDoS атака**\n\n"
                    f"• **IP-адрес:** `{ip}`\n"
                    f"• **Причина:** {reason}\n"
                    f"• **Время:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"IP автоматически разблокируется через {ConfigManager().get('auto_unblock_minutes', 60)} минут."
                )
                await cls._bot_instance.alert_admin(message)
        except Exception as e:
            logger.error(f"Error sending DDoS alert: {str(e)}")