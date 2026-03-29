"""
Advanced Telegram bot with better architecture and error handling.
"""

import asyncio
import tempfile
import os
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

from .config import get_settings
from .logging import get_logger
from .models import Database, Admin, BlockedIP, Session as DBSession
from .face_auth import get_authenticator
from .ip_blocker import get_ip_blocker
from datetime import datetime, timedelta
import secrets

logger = get_logger(__name__)


class TelegramBot:
    """Advanced Telegram bot for DDoS protection system."""
    
    def __init__(self):
        self.settings = get_settings()
        self.db = Database()
        self.authenticator = get_authenticator()
        self.ip_blocker = get_ip_blocker()
        
        # Set IP blocker's Telegram bot reference
        self.ip_blocker.set_telegram_bot(self)
        
        # Bot application
        self.application: Optional[Application] = None
        
        # Conversation states
        self.WAITING_FOR_PHOTO = 1
        self.waiting_for_photo: Dict[int, str] = {}  # user_id -> action
        
        logger.info("Telegram bot initialized")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"/start command from user {user_id} ({user.username})")
        
        # Check if user is authenticated
        if self._is_authenticated(user_id):
            await update.message.reply_text(
                "✅ **Вы аутентифицированы!**\n\n"
                "Доступные команды:\n"
                "• /stats - статистика блокировок\n"
                "• /blocked - список заблокированных IP\n"
                "• /unblock <IP> - разблокировать IP\n"
                "• /status - статус системы\n"
                "• /add_admin - добавить администратора\n"
                "• /list_admins - список администраторов\n"
                "• /remove_admin <ID> - удалить администратора\n"
                "• /whitelist <IP> [описание] - добавить IP в белый список\n"
                "• /whitelist_remove <IP> - удалить IP из белого списка\n"
                "• /whitelist_list - список IP в белом списке\n"
                "• /logout - выйти из системы"
            )
        else:
            await update.message.reply_text(
                "🛡️ **DDoS Protection System**\n\n"
                "Система защиты от DDoS-атак с биометрической аутентификацией.\n\n"
                "Для доступа к командам администратора необходимо аутентифицироваться.\n\n"
                "Используйте команду:\n"
                "• /login - аутентификация по лицу\n\n"
                "Если вы первый администратор, используйте:\n"
                "• /add_first_admin - добавить первого администратора"
            )
    
    async def add_first_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /add_first_admin command."""
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"/add_first_admin command from user {user_id}")
        
        # Check if there are already admins
        session = self.db.get_session()
        existing_admins = session.query(Admin).filter(Admin.is_active == True).count()
        session.close()
        
        if existing_admins > 0:
            await update.message.reply_text(
                "❌ Первый администратор уже добавлен.\n"
                "Используйте /add_admin для добавления новых администраторов."
            )
            return ConversationHandler.END
        
        # Ask for photo
        self.waiting_for_photo[user_id] = 'first_admin'
        
        await update.message.reply_text(
            "👑 **Добавление первого администратора**\n\n"
            "Отправьте четкое фото вашего лица.\n\n"
            "Требования к фото:\n"
            "• Лицо должно быть хорошо видно\n"
            "• Хорошее освещение\n"
            "• Фото должно быть четким\n"
            "• Только одно лицо в кадре\n\n"
            "Отправьте фото или /cancel для отмены."
        )
        
        return self.WAITING_FOR_PHOTO
    
    async def login_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /login command."""
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"/login command from user {user_id}")
        
        # Check if user is already authenticated
        if self._is_authenticated(user_id):
            await update.message.reply_text("✅ Вы уже аутентифицированы.")
            return ConversationHandler.END
        
        # Ask for photo
        self.waiting_for_photo[user_id] = 'login'
        
        await update.message.reply_text(
            "🔐 **Аутентификация**\n\n"
            "Отправьте четкое фото вашего лица для аутентификации.\n\n"
            "Требования к фото:\n"
            "• Лицо должно быть хорошо видно\n"
            "• Хорошее освещение\n"
            "• Фото должно быть четким\n"
            "• Только одно лицо в кадре\n\n"
            "Отправьте фото или /cancel для отмены."
        )
        
        return self.WAITING_FOR_PHOTO
    
    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /add_admin command."""
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"/add_admin command from user {user_id}")
        
        # Check if user is authenticated
        if not self._is_authenticated(user_id):
            await update.message.reply_text("❌ Вы не аутентифицированы. Используйте /login.")
            return ConversationHandler.END
        
        # Ask for photo
        self.waiting_for_photo[user_id] = 'add_admin'
        
        await update.message.reply_text(
            "👤 **Добавление администратора**\n\n"
            "Отправьте четкое фото лица нового администратора.\n\n"
            "Требования к фото:\n"
            "• Лицо должно быть хорошо видно\n"
            "• Хорошее освещение\n"
            "• Фото должно быть четким\n"
            "• Только одно лицо в кадре\n\n"
            "Отправьте фото или /cancel для отмены."
        )
        
        return self.WAITING_FOR_PHOTO
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle photo messages."""
        user = update.effective_user
        user_id = user.id
        
        action = self.waiting_for_photo.pop(user_id, None)
        if not action:
            await update.message.reply_text("❌ Неожиданное фото. Пожалуйста, используйте команду сначала.")
            return ConversationHandler.END
        
        logger.info(f"Photo received from user {user_id} for action: {action}")
        
        # Download photo
        photo_file = await update.message.photo[-1].get_file()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            await photo_file.download_to_drive(temp_file.name)
            
            try:
                if action == 'first_admin':
                    # Add first admin
                    success = self.authenticator.add_admin_face(
                        user_id, user.username or f"user_{user_id}", temp_file.name
                    )
                    
                    if success:
                        # Create session
                        self._create_session(user_id)
                        
                        await update.message.reply_text(
                            "✅ **Первый администратор успешно добавлен!**\n\n"
                            "Теперь вы можете использовать все команды администратора.\n\n"
                            "Используйте /start для просмотра доступных команд."
                        )
                    else:
                        await update.message.reply_text(
                            "❌ **Не удалось добавить администратора.**\n\n"
                            "Возможные причины:\n"
                            "• Лицо не обнаружено на фото\n"
                            "• Плохое качество фото\n"
                            "• Несколько лиц в кадре\n\n"
                            "Попробуйте еще раз с более качественным фото."
                        )
                
                elif action == 'login':
                    # Authenticate user
                    admin = self.authenticator.authenticate(temp_file.name)
                    
                    if admin and admin['user_id'] == user_id:
                        # Create session
                        self._create_session(user_id)
                        
                        await update.message.reply_text(
                            "✅ **Аутентификация успешна!**\n\n"
                            "Теперь у вас есть доступ к командам администратора.\n\n"
                            "Используйте /start для просмотра доступных команд."
                        )
                    else:
                        await update.message.reply_text(
                            "❌ **Аутентификация не удалась.**\n\n"
                            "Возможные причины:\n"
                            "• Ваше лицо не распознано\n"
                            "• Вы не зарегистрированы как администратор\n"
                            "• Плохое качество фото\n\n"
                            "Обратитесь к существующему администратору."
                        )
                
                elif action == 'add_admin':
                    # Check if user is admin
                    if not self._is_admin(user_id):
                        await update.message.reply_text("❌ У вас нет прав для добавления администраторов.")
                        return ConversationHandler.END
                    
                    # Add new admin (using current user's credentials for now)
                    # In a real implementation, you'd need to identify the new admin
                    await update.message.reply_text(
                        "⚠️ **Функция в разработке**\n\n"
                        "Для добавления нового администратора попросите его:\n"
                        "1. Написать боту /start\n"
                        "2. Отправить фото лица\n"
                        "3. Сообщить вам свой user_id\n\n"
                        "Затем используйте команду:\n"
                        "• /register_admin <user_id>"
                    )
                
            except Exception as e:
                logger.error(f"Photo processing error: {e}")
                await update.message.reply_text("❌ Произошла ошибка при обработке фото.")
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
        
        return ConversationHandler.END
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command."""
        user_id = update.effective_user.id
        
        if not self._is_authenticated(user_id):
            await update.message.reply_text("❌ Вы не аутентифицированы. Используйте /login.")
            return
        
        try:
            session = self.db.get_session()
            
            # Get blocked IP count
            blocked_count = session.query(BlockedIP).filter(BlockedIP.is_active == True).count()
            
            # Get total attacks (last 24 hours)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            attacks_24h = session.query(BlockedIP).filter(BlockedIP.blocked_at >= cutoff).count()
            
            # Get admin count
            admin_count = session.query(Admin).filter(Admin.is_active == True).count()
            
            session.close()
            
            await update.message.reply_text(
                f"📊 **Статистика системы**\n\n"
                f"• Заблокировано IP: **{blocked_count}**\n"
                f"• Атак за 24 часа: **{attacks_24h}**\n"
                f"• Администраторов: **{admin_count}**\n"
                f"• Система: **🟢 Активна**"
            )
            
        except Exception as e:
            logger.error(f"Stats command error: {e}")
            await update.message.reply_text("❌ Ошибка при получении статистики.")
    
    async def blocked_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /blocked command."""
        user_id = update.effective_user.id
        
        if not self._is_authenticated(user_id):
            await update.message.reply_text("❌ Вы не аутентифицированы. Используйте /login.")
            return
        
        try:
            blocked_ips = self.ip_blocker.get_blocked_ips()
            
            if not blocked_ips:
                await update.message.reply_text("✅ Нет заблокированных IP-адресов.")
                return
            
            # Show last 10 blocked IPs
            message = "📋 **Последние заблокированные IP:**\n\n"
            for ip_data in blocked_ips[:10]:
                blocked_time = datetime.fromisoformat(ip_data['blocked_at'].replace('Z', '+00:00'))
                time_ago = datetime.utcnow() - blocked_time
                hours_ago = int(time_ago.total_seconds() / 3600)
                minutes_ago = int((time_ago.total_seconds() % 3600) / 60)
                
                message += (
                    f"• `{ip_data['ip_address']}`\n"
                    f"  Причина: {ip_data['reason']}\n"
                    f"  Заблокирован: {hours_ago}ч {minutes_ago}м назад\n\n"
                )
            
            if len(blocked_ips) > 10:
                message += f"\n... и еще {len(blocked_ips) - 10} IP-адресов."
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Blocked command error: {e}")
            await update.message.reply_text("❌ Ошибка при получении списка заблокированных IP.")
    
    async def unblock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /unblock <IP> command."""
        user_id = update.effective_user.id
        
        if not self._is_authenticated(user_id):
            await update.message.reply_text("❌ Вы не аутентифицированы. Используйте /login.")
            return
        
        if not context.args:
            await update.message.reply_text("Использование: /unblock <IP-адрес>")
            return
        
        ip = context.args[0]
        
        try:
            success = self.ip_blocker.unblock_ip(ip)
            
            if success:
                await update.message.reply_text(f"✅ IP `{ip}` разблокирован.")
            else:
                await update.message.reply_text(f"❌ Не удалось разблокировать IP `{ip}`.")
                
        except Exception as e:
            logger.error(f"Unblock command error: {e}")
            await update.message.reply_text(f"❌ Ошибка при разблокировке IP `{ip}`.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        user_id = update.effective_user.id
        
        if not self._is_authenticated(user_id):
            await update.message.reply_text("❌ Вы не аутентифицированы. Используйте /login.")
            return
        
        try:
            # Get system status
            session = self.db.get_session()
            
            # Check database connection
            db_status = "🟢" if session.bind else "🔴"
            
            # Check Redis connection
            redis_status = "🟢" if self.ip_blocker.redis.is_connected() else "🔴"
            
            # Get counts
            blocked_count = session.query(BlockedIP).filter(BlockedIP.is_active == True).count()
            admin_count = session.query(Admin).filter(Admin.is_active == True).count()
            
            session.close()
            
            await update.message.reply_text(
                f"📈 **Статус системы**\n\n"
                f"• База данных: {db_status} Работает\n"
                f"• Redis: {redis_status} {'Подключен' if redis_status == '🟢' else 'Не подключен'}\n"
                f"• Заблокировано IP: **{blocked_count}**\n"
                f"• Администраторов: **{admin_count}**\n"
                f"• Версия: **{self.settings.__class__.__name__}**\n\n"
                f"Система: **🟢 АКТИВНА**"
            )
            
        except Exception as e:
            logger.error(f"Status command error: {e}")
            await update.message.reply_text("❌ Ошибка при получении статуса системы.")
    
    async def list_admins_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /list_admins command."""
        user_id = update.effective_user.id
        
        if not self._is_authenticated(user_id):
            await update.message.reply_text("❌ Вы не аутентифицированы. Используйте /login.")
            return
        
        try:
            session = self.db.get_session()
            admins = session.query(Admin).filter(Admin.is_active == True).all()
            session.close()
            
            if not admins:
                await update.message.reply_text("❌ В системе нет администраторов.")
                return
            
            message = "👥 **Список администраторов:**\n\n"
            for admin in admins:
                created_at = admin.created_at
                if created_at:
                    days_ago = (datetime.utcnow() - created_at).days
                    created_str = f"{days_ago} дней назад"
                else:
                    created_str = "неизвестно"
                
                message += (
                    f"• **ID:** `{admin.user_id}`\n"
                    f"  **Имя:** @{admin.username}\n"
                    f"  **Добавлен:** {created_str}\n\n"
                )
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"List admins command error: {e}")
            await update.message.reply_text("❌ Ошибка при получении списка администраторов.")
    
    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /remove_admin <ID> command."""
        user_id = update.effective_user.id
        
        if not self._is_authenticated(user_id):
            await update.message.reply_text("❌ Вы не аутентифицированы. Используйте /login.")
            return
        
        if not context.args:
            await update.message.reply_text("Использование: /remove_admin <user_id>")
            return
        
        try:
            target_user_id = int(context.args[0])
            
            # Check if trying to remove self
            if target_user_id == user_id:
                await update.message.reply_text("❌ Вы не можете удалить себя.")
                return
            
            session = self.db.get_session()
            
            # Check if target user exists
            target_admin = session.query(Admin).filter(Admin.user_id == target_user_id).first()
            
            if not target_admin:
                await update.message.reply_text(f"❌ Администратор с ID {target_user_id} не найден.")
                session.close()
                return
            
            # Remove admin
            session.delete(target_admin)
            session.commit()
            session.close()
            
            # Reload authenticator faces
            self.authenticator._load_known_faces()
            
            await update.message.reply_text(f"✅ Администратор {target_user_id} удален.")
            
        except ValueError:
            await update.message.reply_text("❌ Неверный формат user_id. Используйте числовой ID.")
        except Exception as e:
            logger.error(f"Remove admin command error: {e}")
            await update.message.reply_text("❌ Ошибка при удалении администратора.")
    
    async def logout_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /logout command."""
        user_id = update.effective_user.id
        
        try:
            session = self.db.get_session()
            db_session = session.query(DBSession).filter(DBSession.user_id == user_id).first()
            
            if db_session:
                session.delete(db_session)
                session.commit()
            
            session.close()
            
            await update.message.reply_text("✅ Вы вышли из системы.")
            
        except Exception as e:
            logger.error(f"Logout command error: {e}")
            await update.message.reply_text("❌ Ошибка при выходе из системы.")
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /cancel command."""
        user_id = update.effective_user.id
        
        if user_id in self.waiting_for_photo:
            del self.waiting_for_photo[user_id]
        
        await update.message.reply_text("❌ Операция отменена.")
        return ConversationHandler.END
    
    async def send_admin_message(self, message: str) -> None:
        """Send message to admin chat."""
        try:
            if self.application:
                await self.application.bot.send_message(
                    chat_id=self.settings.admin_chat_id,
                    text=message,
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Failed to send admin message: {e}")
    
    def _is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        try:
            session = self.db.get_session()
            admin = session.query(Admin).filter(
                Admin.user_id == user_id,
                Admin.is_active == True
            ).first()
            session.close()
            
            return admin is not None
        except Exception as e:
            logger.error(f"Failed to check if user {user_id} is admin: {e}")
            return False
    
    def _is_authenticated(self, user_id: int) -> bool:
        """Check if user is authenticated (has valid session)."""
        try:
            session = self.db.get_session()
            db_session = session.query(DBSession).filter(
                DBSession.user_id == user_id,
                DBSession.is_valid == True,
                DBSession.expires_at > datetime.utcnow()
            ).first()
            session.close()
            
            if db_session:
                # Update last activity
                session = self.db.get_session()
                db_session.last_activity = datetime.utcnow()
                session.commit()
                session.close()
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to check authentication for user {user_id}: {e}")
            return False
    
    def _create_session(self, user_id: int) -> None:
        """Create a new session for user."""
        try:
            session = self.db.get_session()
            
            # Remove old sessions for this user
            old_sessions = session.query(DBSession).filter(DBSession.user_id == user_id).all()
            for old_session in old_sessions:
                session.delete(old_session)
            
            # Create new session
            new_session = DBSession(
                user_id=user_id,
                session_token=secrets.token_hex(32),
                expires_at=datetime.utcnow() + timedelta(minutes=self.settings.session_timeout_minutes),
                is_valid=True
            )
            
            session.add(new_session)
            session.commit()
            session.close()
            
            logger.info(f"Session created for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
    
    def setup_handlers(self) -> None:
        """Setup bot command handlers."""
        # Conversation handler for photo-based commands
        photo_conversation = ConversationHandler(
            entry_points=[
                CommandHandler("add_first_admin", self.add_first_admin_command),
                CommandHandler("login", self.login_command),
                CommandHandler("add_admin", self.add_admin_command),
            ],
            states={
                self.WAITING_FOR_PHOTO: [
                    MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, self.handle_photo),
                    CommandHandler("cancel", self.cancel_command),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_command)],
        )
        
        # Regular command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(photo_conversation)
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("blocked", self.blocked_command))
        self.application.add_handler(CommandHandler("unblock", self.unblock_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("list_admins", self.list_admins_command))
        self.application.add_handler(CommandHandler("remove_admin", self.remove_admin_command))
        self.application.add_handler(CommandHandler("logout", self.logout_command))
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors in bot."""
        logger.error(f"Bot error: {context.error}", exc_info=context.error)
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка. Пожалуйста, попробуйте позже."
                )
            except:
                pass
    
    async def run(self) -> None:
        """Run the Telegram bot."""
        try:
            self.application = Application.builder().token(self.settings.bot_token).build()
            self.setup_handlers()
            
            logger.info("Starting Telegram bot...")
            
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Telegram bot started successfully")
            
            # Keep bot running
            while True:
                await asyncio.sleep(3600)
                
        except Exception as e:
            logger.error(f"Failed to run Telegram bot: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self.application:
            logger.info("Stopping Telegram bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram bot stopped")


# Global bot instance
telegram_bot = TelegramBot()


def get_telegram_bot() -> TelegramBot:
    """Get Telegram bot instance."""
    return telegram_bot
