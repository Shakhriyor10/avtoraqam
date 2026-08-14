# Развёртывание Avtoraqam CRM на Ubuntu

Расчётная схема: Ubuntu 22.04/24.04, PostgreSQL, Gunicorn, Nginx, HTTPS и отдельный постоянно работающий systemd-сервис Telegram-бота.

## 1. Установка пакетов

```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip postgresql postgresql-contrib nginx certbot python3-certbot-nginx
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

## 2. Пользователь и проект

```bash
sudo useradd --system --create-home --shell /bin/bash avtoraqam
sudo mkdir -p /var/www/avtoraqam
sudo chown -R avtoraqam:www-data /var/www/avtoraqam
sudo -u avtoraqam git clone https://github.com/Shakhriyor10/avtoraqam.git /var/www/avtoraqam
sudo -u avtoraqam python3 -m venv /var/www/avtoraqam/.venv
sudo -u avtoraqam /var/www/avtoraqam/.venv/bin/pip install --upgrade pip
sudo -u avtoraqam /var/www/avtoraqam/.venv/bin/pip install -r /var/www/avtoraqam/requirements.txt
```

Если файлы загружаются через SFTP, поместите содержимое проекта в `/var/www/avtoraqam`, не копируя локальные `.venv`, `.env`, `db.sqlite3` и `staticfiles`.

## 3. PostgreSQL

Замените пароль на длинный уникальный пароль:

```bash
sudo -u postgres psql
```

```sql
CREATE USER avtoraqam WITH PASSWORD 'CHANGE_ME_STRONG_DATABASE_PASSWORD';
CREATE DATABASE avtoraqam OWNER avtoraqam;
\q
```

PostgreSQL оставляем доступным только локально; порт 5432 в UFW открывать не нужно.

## 4. Переменные окружения

```bash
sudo -u avtoraqam cp /var/www/avtoraqam/.env.example /var/www/avtoraqam/.env
sudo -u avtoraqam nano /var/www/avtoraqam/.env
sudo chmod 640 /var/www/avtoraqam/.env
sudo chown avtoraqam:www-data /var/www/avtoraqam/.env
```

Секретный ключ можно получить командой:

```bash
openssl rand -base64 48
```

Обязательно укажите домен/IP, `DJANGO_DEBUG=false`, пароль PostgreSQL, токен и ID Telegram-группы. Для запуска сначала только по IP укажите:

```env
DJANGO_ALLOWED_HOSTS=YOUR_SERVER_IP
DJANGO_CSRF_TRUSTED_ORIGINS=http://YOUR_SERVER_IP
DJANGO_SECURE_SSL_REDIRECT=false
DJANGO_SECURE_HSTS_SECONDS=0
```

После подключения HTTPS замените origin на `https://YOUR_DOMAIN` и включите SSL redirect/HSTS.

## 5. Подготовка Django

```bash
cd /var/www/avtoraqam
sudo -u avtoraqam .venv/bin/python manage.py migrate --noinput
sudo -u avtoraqam .venv/bin/python manage.py collectstatic --noinput
sudo -u avtoraqam .venv/bin/python manage.py createsuperuser
sudo -u avtoraqam .venv/bin/python manage.py check --deploy
```

## 6. Gunicorn и Telegram-бот

```bash
sudo cp /var/www/avtoraqam/deploy/avtoraqam.service /etc/systemd/system/
sudo cp /var/www/avtoraqam/deploy/avtoraqam-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now avtoraqam.service avtoraqam-bot.service
sudo systemctl status avtoraqam.service avtoraqam-bot.service
```

Запускайте только один экземпляр бота, иначе Telegram polling и уведомления будут дублироваться.

## 7. Nginx и HTTPS

В конфиге замените `YOUR_DOMAIN` на реальный домен:

```bash
sudo cp /var/www/avtoraqam/deploy/nginx-avtoraqam.conf /etc/nginx/sites-available/avtoraqam
sudo nano /etc/nginx/sites-available/avtoraqam
sudo ln -s /etc/nginx/sites-available/avtoraqam /etc/nginx/sites-enabled/avtoraqam
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d YOUR_DOMAIN -d www.YOUR_DOMAIN
```

После Certbot включите в `.env`:

```env
DJANGO_ALLOWED_HOSTS=YOUR_DOMAIN,www.YOUR_DOMAIN
DJANGO_CSRF_TRUSTED_ORIGINS=https://YOUR_DOMAIN,https://www.YOUR_DOMAIN
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_SECURE_HSTS_SECONDS=31536000
```

```bash
sudo systemctl restart avtoraqam.service avtoraqam-bot.service
```

## Проверка и диагностика

```bash
curl -I https://YOUR_DOMAIN/login/
sudo journalctl -u avtoraqam.service -n 100 --no-pager
sudo journalctl -u avtoraqam-bot.service -n 100 --no-pager
sudo nginx -t
sudo systemctl status postgresql nginx avtoraqam avtoraqam-bot
```

Проверка бота: добавьте его в группу, разрешите отправку сообщений и выполните `/expiring@ИмяБота`.

## Обновление

```bash
cd /var/www/avtoraqam
sudo -u avtoraqam git pull --ff-only
sudo -u avtoraqam .venv/bin/pip install -r requirements.txt
sudo -u avtoraqam .venv/bin/python manage.py migrate --noinput
sudo -u avtoraqam .venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart avtoraqam.service avtoraqam-bot.service
```

## Резервные копии

Ежедневно сохраняйте и базу, и каталог `media`:

```bash
sudo -u postgres pg_dump -Fc avtoraqam > /path/to/backup/avtoraqam_$(date +%F).dump
sudo tar -czf /path/to/backup/media_$(date +%F).tar.gz /var/www/avtoraqam/media
```

Копии следует переносить на другой сервер или в защищённое облако. В базе находятся персональные данные, поэтому доступ к серверу, `.env`, резервным копиям и каталогу `media` должен быть ограничен.
