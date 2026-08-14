import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = 'Проверяет подключение Telegram-бота и отправляет сообщение в настроенную группу.'

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            raise CommandError('Укажите TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID.')
        url = f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage'
        text = (
            '✅ Avtoraqam CRM подключена\n\n'
            'Telegram-бот успешно настроен для этой группы.\n'
            f'Время проверки: {timezone.localtime():%d.%m.%Y %H:%M}\n\n'
            'Сюда будут приходить уведомления об истекающих услугах и прикреплённые документы.'
        )
        payload = urlencode({'chat_id': settings.TELEGRAM_CHAT_ID, 'text': text}).encode()
        try:
            with urlopen(Request(url, data=payload), timeout=20) as response:
                result = json.loads(response.read())
        except Exception as error:
            raise CommandError(f'Не удалось подключиться к Telegram: {error}') from error
        if not result.get('ok'):
            raise CommandError(result.get('description', 'Ошибка Telegram API'))
        chat = result['result']['chat']
        self.stdout.write(self.style.SUCCESS(
            f'Сообщение отправлено. Группа: {chat.get("title", chat.get("id"))}, chat_id: {chat.get("id")}'
        ))
