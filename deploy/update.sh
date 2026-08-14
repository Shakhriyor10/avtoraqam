#!/usr/bin/env bash
set -euo pipefail

cd /var/www/avtoraqam
git pull --ff-only
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
sudo systemctl restart avtoraqam.service avtoraqam-bot.service
sudo systemctl --no-pager --full status avtoraqam.service avtoraqam-bot.service
