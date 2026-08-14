import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from crm.telegram_bot.handlers import router
from crm.telegram_bot.services import send_due_notifications


async def notification_loop(bot, chat_id, interval):
    interval = max(int(interval), 60)
    while True:
        try:
            await send_due_notifications(bot, chat_id)
        except Exception:
            logging.exception('Ошибка фоновой отправки Telegram-уведомлений')
        await asyncio.sleep(interval)


async def run_bot():
    bot = Bot(settings.TELEGRAM_BOT_TOKEN)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    await bot.set_my_commands([
        BotCommand(command='start', description='Открыть меню'),
        BotCommand(command='status', description='Статистика CRM'),
        BotCommand(command='expiring', description='Истекающие услуги'),
        BotCommand(command='help', description='Помощь'),
    ])
    task = asyncio.create_task(notification_loop(
        bot, settings.TELEGRAM_CHAT_ID, settings.TELEGRAM_CHECK_INTERVAL_SECONDS
    ))
    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await bot.session.close()


class Command(BaseCommand):
    help = 'Запускает постоянно работающего Telegram-бота Avtoraqam CRM (aiogram 3).'

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            raise CommandError('Укажите TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID.')
        logging.basicConfig(level=logging.INFO)
        self.stdout.write(self.style.SUCCESS('Telegram-бот запущен. Для остановки нажмите Ctrl+C.'))
        asyncio.run(run_bot())
