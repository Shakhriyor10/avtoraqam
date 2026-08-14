import asyncio

from aiogram import Bot
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from crm.telegram_bot.services import send_due_notifications


class Command(BaseCommand):
    help = 'Один раз проверяет сроки и отправляет Telegram-уведомления через aiogram 3.'

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            raise CommandError('Укажите TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID.')
        sent = asyncio.run(self._send())
        self.stdout.write(self.style.SUCCESS(f'Отправлено уведомлений: {sent}'))

    async def _send(self):
        bot = Bot(settings.TELEGRAM_BOT_TOKEN)
        try:
            return await send_due_notifications(bot, settings.TELEGRAM_CHAT_ID)
        finally:
            await bot.session.close()
