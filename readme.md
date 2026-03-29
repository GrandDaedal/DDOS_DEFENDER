# 🛡️ Advanced DDoS Protection System v2.0

**Автономная система защиты от DDoS-атак с биометрической аутентификацией через Telegram бота.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## ✨ Возможности

### 🚀 **Основные функции**
- 🔍 **Мониторинг трафика** в реальном времени на указанном порту
- 🚨 **Автоматическая блокировка** IP при превышении порога пакетов/секунду
- 📱 **Уведомления в Telegram** о блокировках и атаках
- 🔐 **Биометрическая аутентификация** по лицу с использованием deep learning
- ⏱️ **Авторазблокировка** через заданное время
- 🐳 **Полная контейнеризация** через Docker Compose

### 🏗️ **Улучшенная архитектура**
- 🎯 **Асинхронная архитектура** на основе asyncio
- 📊 **Скользящее окно** для точного подсчета rate limiting
- 🗄️ **База данных SQLite/PostgreSQL** для хранения данных
- 🔄 **Redis кэширование** для распределенной блокировки
- 📈 **Мониторинг и метрики** через Prometheus + Grafana
- 🪵 **Структурированное логирование** в JSON формате

### 🔒 **Безопасность**
- 🤖 **Face Recognition** с использованием dlib и face_recognition
- 🔑 **Сессии с таймаутом** для администраторов
- 📋 **Белый список** IP-адресов
- 🛡️ **Многоуровневая защита** через iptables и Redis

## 🚀 Быстрый старт

### 1. Предварительные требования
- **Docker** и **Docker Compose**
- **Сервер с Linux** (рекомендуется VPS с Ubuntu 22.04+)
- **Telegram бот** (создать через [@BotFather](https://t.me/BotFather))
- **Доступ к сети** с правами администратора

### 2. Настройка окружения

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd ddos_defender

# Скопируйте пример конфигурации
cp .env.example .env

# Отредактируйте .env файл
nano .env
```

**Обязательные параметры в .env:**
```env
DDOS_BOT_TOKEN=your_bot_token_here          # Токен от @BotFather
DDOS_ADMIN_CHAT_ID=your_chat_id_here        # ID чата администратора
DDOS_MONITOR_INTERFACE=eth0                 # Сетевой интерфейс
DDOS_MONITOR_PORT=80                        # Порт для мониторинга
```

### 3. Запуск системы

```bash
# Сборка и запуск
docker-compose build --no-cache
docker-compose up -d

# Просмотр логов
docker-compose logs -f ddos-protection

# Проверка статуса
docker-compose ps
```

### 4. Регистрация первого администратора

1. **Найдите бота в Telegram** по имени
2. **Отправьте команду:** `/start`
3. **Добавьте первого администратора:** `/add_first_admin`
4. **Отправьте четкое фото вашего лица**
5. **Готово!** Вы зарегистрированы как администратор

### 5. Аутентификация администраторов

Для доступа к командам используйте:
```text
/login - аутентификация по лицу
```

## 📋 Команды бота

### 📊 Основные команды
- `/stats` - статистика блокировок и атак
- `/blocked` - список заблокированных IP
- `/unblock <IP>` - разблокировать указанный IP
- `/status` - статус системы и компонентов
- `/logout` - выйти из системы

### 👥 Административные команды
- `/add_admin` - добавить нового администратора
- `/list_admins` - список всех администраторов
- `/remove_admin <ID>` - удалить администратора
- `/whitelist <IP> [описание]` - добавить IP в белый список
- `/whitelist_remove <IP>` - удалить IP из белого списка
- `/whitelist_list` - список IP в белом списке

## 🏗️ Архитектура системы

### Компоненты
1. **Traffic Analyzer** - анализ сетевого трафика, обнаружение атак
2. **IP Blocker** - блокировка IP через iptables и Redis
3. **Face Authenticator** - биометрическая аутентификация
4. **Telegram Bot** - управление через Telegram
5. **Database Layer** - хранение данных (SQLite/PostgreSQL)
6. **Monitoring** - метрики и мониторинг (Prometheus/Grafana)

### Стек технологий
- **Python 3.11+** - основной язык разработки
- **asyncio** - асинхронное программирование
- **Scapy** - анализ сетевых пакетов
- **face_recognition** - распознавание лиц
- **SQLAlchemy** - ORM для работы с БД
- **Redis** - кэширование и распределенные блокировки
- **Docker** - контейнеризация
- **Prometheus** - сбор метрик
- **Grafana** - визуализация метрик

## ⚙️ Конфигурация

### Основные параметры
| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `DDOS_BLOCK_THRESHOLD` | 1000 | Порог пакетов/секунду для блокировки |
| `DDOS_AUTO_UNBLOCK_MINUTES` | 60 | Время авторазблокировки (минуты) |
| `DDOS_RATE_WINDOW_SECONDS` | 10 | Размер скользящего окна (секунды) |
| `DDOS_FACE_SIMILARITY_THRESHOLD` | 0.6 | Порог схожести лиц (0.0-1.0) |
| `DDOS_WORKER_COUNT` | 4 | Количество воркеров для обработки пакетов |
| `DDOS_MAX_QUEUE_SIZE` | 10000 | Максимальный размер очереди пакетов |

### Мониторинг
Система предоставляет метрики через Prometheus:
- **Порт:** 9090
- **Эндпоинт:** `/metrics`

Grafana доступна по адресу:
- **URL:** http://localhost:3000
- **Логин:** `admin`
- **Пароль:** из переменной `GRAFANA_PASSWORD`

## 🐳 Docker Compose сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| `ddos-protection` | 8080, 9090 | Основное приложение |
| `redis` | 6379 | Кэш и распределенные блокировки |
| `prometheus` | 9091 | Сбор метрик |
| `grafana` | 3000 | Визуализация метрик |

## 🔧 Разработка

### Установка для разработки
```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Инициализация базы данных
python -m ddos_defender.main --init-db

# Запуск в режиме разработки
python -m ddos_defender.main
```

### Тестирование
```bash
# Установка тестовых зависимостей
pip install pytest pytest-asyncio

# Запуск тестов
pytest tests/ -v
```

### Линтинг
```bash
# Проверка стиля кода
black ddos_defender/
flake8 ddos_defender/
mypy ddos_defender/
```

## 📊 Мониторинг и метрики

### Доступные метрики
- `ddos_packets_total` - общее количество обработанных пакетов
- `ddos_attacks_detected` - обнаруженные атаки
- `ddos_ips_blocked` - заблокированные IP
- `ddos_queue_size` - размер очереди пакетов
- `ddos_whitelist_size` - размер белого списка

### Дашборды Grafana
Система включает предварительно настроенные дашборды:
1. **Обзор системы** - общая статистика и состояние
2. **Атаки в реальном времени** - обнаруженные атаки
3. **Производительность** - метрики производительности
4. **Безопасность** - статистика аутентификации

## 🔒 Безопасность

### Рекомендации по безопасности
1. **Используйте сильные пароли** для Redis и Grafana
2. **Ограничьте доступ** к портам мониторинга
3. **Регулярно обновляйте** зависимости
4. **Мониторьте логи** на предмет подозрительной активности
5. **Используйте VPN** для доступа к административным интерфейсам

### Аутентификация
- **Face Recognition** с порогом схожести 0.6
- **Сессии** с таймаутом 30 минут
- **Многофакторная аутентификация** через Telegram + лицо

## 🚨 Устранение неполадок

### Общие проблемы

**Проблема:** Бот не запускается
```bash
# Проверьте токен бота
docker-compose logs ddos-protection | grep "Bot token"

# Проверьте подключение к Telegram API
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

**Проблема:** Не работает блокировка IP
```bash
# Проверьте права доступа
docker exec ddos_protection iptables -L -n

# Проверьте Redis
docker exec ddos_redis redis-cli ping
```

**Проблема:** Не работает распознавание лиц
```bash
# Проверьте наличие моделей dlib
docker exec ddos_protection python -c "import dlib; print(dlib.__version__)"

# Проверьте качество фото (требования в /add_first_admin)
```

### Логи
```bash
# Просмотр логов приложения
docker-compose logs ddos-protection

# Просмотр логов Redis
docker-compose logs redis

# Просмотр логов в реальном времени
docker-compose logs -f ddos-protection
```

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для получения дополнительной информации.

## 🤝 Вклад в проект

Мы приветствуем вклады! Пожалуйста, ознакомьтесь с [CONTRIBUTING.md](CONTRIBUTING.md) для получения подробной информации.

## 📞 Поддержка

- **Issues:** [GitHub Issues](https://github.com/yourusername/ddos_defender/issues)
- **Telegram:** [@your_bot_username](https://t.me/your_bot_username)
- **Документация:** [Wiki](https://github.com/yourusername/ddos_defender/wiki)

---

**🚀 Защитите свой сервер от DDoS-атак с помощью современной системы безопасности!**