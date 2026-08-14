# Avtoraqam CRM

CRM для учёта клиентов, автомобилей, документов и сроков автомобильных услуг.

## PostgreSQL

Основная база проекта — PostgreSQL. Создайте пользователя и базу, затем заполните `.env`:

```env
POSTGRES_DB=avtoraqam
POSTGRES_USER=avtoraqam
POSTGRES_PASSWORD=НАДЕЖНЫЙ_ПАРОЛЬ
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
USE_SQLITE=false
```

После создания базы выполните:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Для временного локального запуска на SQLite можно установить `USE_SQLITE=true`. Автоматические тесты используют SQLite независимо от рабочей базы.

## Локальный запуск (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Откройте `http://127.0.0.1:8000/` и войдите с учётной записью администратора.

## Telegram-уведомления

Перед запуском укажите переменные окружения:

```powershell
$env:TELEGRAM_BOT_TOKEN='токен_бота'
$env:TELEGRAM_CHAT_ID='идентификатор_группы'
python manage.py notify_expiring
```

Настройка группы:

1. Создайте Telegram-группу и добавьте в неё бота.
2. Выдайте боту право отправлять сообщения и файлы.
3. Отправьте любое сообщение в группу.
4. Откройте `https://api.telegram.org/bot<ТОКЕН>/getUpdates` и найдите `chat.id` группы (обычно отрицательное число вида `-100...`).
5. Укажите токен и `chat_id`, затем проверьте подключение:

```powershell
$env:TELEGRAM_BOT_TOKEN='123456:ABC...'
$env:TELEGRAM_CHAT_ID='-1001234567890'
.\.venv\Scripts\python.exe manage.py telegram_test
.\.venv\Scripts\python.exe manage.py notify_expiring
```

При наступлении настроенного срока бот отправляет вид услуги, клиента, телефон, автомобиль, дату оформления, дату окончания и количество оставшихся дней. После сообщения отправляются все файлы, прикреплённые к услуге.

## Постоянный aiogram 3-бот

Создайте `.env` рядом с `manage.py` на основе `.env.example`:

```env
TELEGRAM_BOT_TOKEN=123456789:ABC...
TELEGRAM_CHAT_ID=-1001234567890
TELEGRAM_CHECK_INTERVAL_SECONDS=3600
```

Файл `.env` исключён из Git и не попадёт в репозиторий.

```powershell
.\.venv\Scripts\python.exe manage.py runbot
```

Бот работает постоянно через long polling, раз в час проверяет сроки и один раз в день отправляет каждое актуальное предупреждение. Интервал проверки можно изменить через `TELEGRAM_CHECK_INTERVAL_SECONDS`. Команды `/start`, `/status`, `/expiring` и `/help` доступны только в настроенной группе. Несколько документов одной услуги отправляются одной медиагруппой; полная информация об услуге находится в подписи последнего файла.

Команду `notify_expiring` следует запускать ежедневно через планировщик задач. По умолчанию она предупреждает за 14 дней; период настраивается переменной `EXPIRY_WARNING_DAYS`.
