from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from config_manager import ConfigManager
from data_manager import DataManager
from face_auth import FaceAuth
from session_manager import SessionManager
from ip_blocker import IPBlocker
from file_logger import logger
import tempfile
import os
import asyncio

class DDoSTelegramBot:
    def __init__(self):
        self.config = ConfigManager()
        self.application = None
        self.waiting_for_photo = {}  # user_id -> action

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        # Проверяем, есть ли администраторы в системе
        existing_admins = DataManager.get_admins()
        
        if not existing_admins:
            await update.message.reply_text(
                "🚀 DDoS Protection System Bot\n\n"
                "Система активирована. Для начала работы необходимо добавить первого администратора.\n\n"
                "Используйте команду: /add_first_admin"
            )
        elif SessionManager.validate_session(user_id):
            await update.message.reply_text(
                "✅ Вы аутентифицированы. Доступные команды:\n"
                "/stats - статистика блокировок\n"
                "/blocked - список заблокированных IP\n"
                "/unblock <IP> - разблокировать IP\n"
                "/status - статус системы\n"
                "/add_admin - добавить администратора\n"
                "/list_admins - список администраторов"
            )
        else:
            await update.message.reply_text(
                "🔐 DDoS Protection System Bot\n\n"
                "Используйте /login для аутентификации с помощью лица."
            )

    async def add_first_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Одноразовая команда для добавления первого администратора"""
        user_id = update.message.from_user.id
        
        # Проверяем, есть ли уже администраторы
        existing_admins = DataManager.get_admins()
        if existing_admins:
            await update.message.reply_text("❌ Первый администратор уже добавлен. Используйте /add_admin для добавления новых администраторов.")
            return
        
        self.waiting_for_photo[user_id] = 'first_admin'
        await update.message.reply_text(
            "👑 Добавление первого администратора\n\n"
            "Отправьте четкое фото вашего лица. После этого вы станете администратором системы."
        )

    async def login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        self.waiting_for_photo[user_id] = 'login'
        await update.message.reply_text("📸 Пожалуйста, отправьте четкое фото вашего лица для аутентификации.")

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not SessionManager.validate_session(update.message.from_user.id):
            await update.message.reply_text("🚫 Сессия истекла. Пожалуйста, выполните /login снова.")
            return
        blocked_count = len(DataManager.get_blocked_ips())
        await update.message.reply_text(f"📊 Заблокировано IP-адресов: {blocked_count}")

    async def blocked(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not SessionManager.validate_session(update.message.from_user.id):
            await update.message.reply_text("🚫 Сессия истекла. Пожалуйста, выполните /login снова.")
            return
        blocked_ips = DataManager.get_blocked_ips()
        if not blocked_ips:
            await update.message.reply_text("✅ Нет заблокированных IP-адресов")
            return
            
        message = "📋 Последние заблокированные IP:\n\n"
        for ip_data in blocked_ips[-10:]:
            message += f"• {ip_data['ip']} - {ip_data['reason']}\n"
        
        await update.message.reply_text(message)

    async def unblock(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not SessionManager.validate_session(update.message.from_user.id):
            await update.message.reply_text("🚫 Сессия истекла. Пожалуйста, выполните /login снова.")
            return
        if not context.args:
            await update.message.reply_text("Использование: /unblock <IP-адрес>")
            return
        ip = context.args[0]
        IPBlocker.unblock_ip(ip)
        await update.message.reply_text(f"✅ IP {ip} разблокирован")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not SessionManager.validate_session(update.message.from_user.id):
            await update.message.reply_text("🚫 Сессия истекла. Пожалуйста, выполните /login снова.")
            return
        await update.message.reply_text("🟢 Система активна и работает")

    async def add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not SessionManager.validate_session(update.message.from_user.id):
            await update.message.reply_text("🚫 Сессия истекла. Пожалуйста, выполните /login снова.")
            return
        user_id = update.message.from_user.id
        self.waiting_for_photo[user_id] = 'add_admin'
        await update.message.reply_text("👤 Отправьте четкое фото для добавления нового администратора")

    async def list_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not SessionManager.validate_session(update.message.from_user.id):
            await update.message.reply_text("🚫 Сессия истекла. Пожалуйста, выполните /login снова.")
            return
        admins = DataManager.get_admins()
        if not admins:
            await update.message.reply_text("❌ В системе нет администраторов")
            return
            
        message = "👥 Список администраторов:\n\n"
        for admin in admins:
            message += f"• ID: {admin['user_id']} - @{admin['username']}\n"
        
        await update.message.reply_text(message)

    async def remove_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not SessionManager.validate_session(update.message.from_user.id):
            await update.message.reply_text("🚫 Сессия истекла. Пожалуйста, выполните /login снова.")
            return
        if not context.args:
            await update.message.reply_text("Использование: /remove_admin <user_id>")
            return
        user_id = int(context.args[0])
        DataManager.remove_admin(user_id)
        await update.message.reply_text(f"✅ Администратор {user_id} удален")

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        action = self.waiting_for_photo.pop(user_id, None)
        
        if not action:
            await update.message.reply_text("❌ Пожалуйста, сначала используйте команду /add_first_admin, /login или /add_admin")
            return

        photo_file = await update.message.photo[-1].get_file()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            await photo_file.download_to_drive(temp_file.name)
            try:
                if action == 'first_admin':
                    encoding = FaceAuth.encode_face(temp_file.name)
                    if encoding:
                        DataManager.add_admin({
                            'user_id': user_id,
                            'username': update.message.from_user.username or f"user_{user_id}",
                            'face_encoding': encoding
                        })
                        SessionManager.create_session(user_id)
                        await update.message.reply_text(
                            "✅ Первый администратор успешно добавлен!\n\n"
                            "Теперь вы можете использовать все команды:\n"
                            "/stats - статистика\n"
                            "/blocked - заблокированные IP\n"
                            "/add_admin - добавить администратора\n"
                            "и другие..."
                        )
                    else:
                        await update.message.reply_text("❌ Не удалось обработать лицо. Отправьте четкое фото с видимым лицом.")
                
                elif action == 'login':
                    admin = FaceAuth.authenticate_user(temp_file.name)
                    if admin:
                        SessionManager.create_session(user_id)
                        await update.message.reply_text("✅ Аутентификация успешна! Теперь у вас есть доступ к командам администратора.")
                    else:
                        await update.message.reply_text("❌ Аутентификация не удалась. Убедитесь, что ваше лицо четко видно.")
                
                elif action == 'add_admin':
                    encoding = FaceAuth.encode_face(temp_file.name)
                    if encoding:
                        DataManager.add_admin({
                            'user_id': user_id,
                            'username': update.message.from_user.username or f"user_{user_id}",
                            'face_encoding': encoding
                        })
                        await update.message.reply_text("✅ Администратор успешно добавлен!")
                    else:
                        await update.message.reply_text("❌ Не удалось обработать лицо. Отправьте четкое фото с видимым лицом.")
            
            except Exception as e:
                logger.error(f"Photo processing error: {str(e)}")
                await update.message.reply_text("❌ Произошла ошибка при обработке фото.")
            finally:
                os.unlink(temp_file.name)

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("add_first_admin", self.add_first_admin))
        self.application.add_handler(CommandHandler("login", self.login))
        self.application.add_handler(CommandHandler("stats", self.stats))
        self.application.add_handler(CommandHandler("blocked", self.blocked))
        self.application.add_handler(CommandHandler("unblock", self.unblock))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("add_admin", self.add_admin))
        self.application.add_handler(CommandHandler("list_admins", self.list_admins))
        self.application.add_handler(CommandHandler("remove_admin", self.remove_admin))
        
        self.application.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, self.handle_photo))

    async def run(self):
        token = self.config.get('bot_token')
        if not token:
            raise ValueError("Bot token not configured")

        self.application = Application.builder().token(token).build()
        self.setup_handlers()
        
        logger.info("Telegram bot starting...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Telegram bot started successfully")
        
        # Keep the bot running
        while True:
            await asyncio.sleep(3600)

    async def stop(self):
        if self.application:
            logger.info("Stopping telegram bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()