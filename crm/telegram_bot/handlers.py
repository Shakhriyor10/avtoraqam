from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from asgiref.sync import sync_to_async
from django.conf import settings

from .services import dashboard_counts, expiring_records, notification_text

router = Router()
try:
    allowed_chat_id = int(settings.TELEGRAM_CHAT_ID)
except (TypeError, ValueError):
    allowed_chat_id = settings.TELEGRAM_CHAT_ID
router.message.filter(F.chat.id == allowed_chat_id)
router.callback_query.filter(F.message.chat.id == allowed_chat_id)


def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⚠️ Истекающие услуги', callback_data='expiring')],
        [InlineKeyboardButton(text='📊 Статистика CRM', callback_data='status')],
    ])


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        '🚗 <b>Avtoraqam CRM Bot</b>\n\nЯ контролирую сроки услуг и отправляю документы в эту группу.',
        parse_mode='HTML', reply_markup=menu(),
    )


@router.message(Command('help'))
async def help_command(message: Message):
    await message.answer('/status — статистика CRM\n/expiring — услуги, требующие внимания\n/help — список команд', reply_markup=menu())


async def send_status(target):
    counts = await sync_to_async(dashboard_counts, thread_sensitive=True)()
    await target.answer(
        '📊 <b>Avtoraqam CRM</b>\n\n'
        f'Клиентов: <b>{counts["clients"]}</b>\nАвтомобилей: <b>{counts["vehicles"]}</b>\n'
        f'Услуг: <b>{counts["services"]}</b>\nСкоро истекают: <b>{counts["warning"]}</b>\n'
        f'Просрочены: <b>{counts["expired"]}</b>', parse_mode='HTML', reply_markup=menu(),
    )


@router.message(Command('status'))
async def status_command(message: Message):
    await send_status(message)


@router.callback_query(F.data == 'status')
async def status_callback(callback: CallbackQuery):
    await callback.answer()
    await send_status(callback.message)


async def send_expiring(target):
    records = await sync_to_async(expiring_records, thread_sensitive=True)()
    if not records:
        await target.answer('✅ Услуг, требующих внимания, сейчас нет.', reply_markup=menu())
        return
    await target.answer(f'⚠️ Найдено услуг: {len(records)}')
    for service in records[:20]:
        await target.answer(notification_text(service), parse_mode='HTML')
    if len(records) > 20:
        await target.answer(f'Показаны первые 20 из {len(records)}. Полный список доступен в CRM.')


@router.message(Command('expiring'))
async def expiring_command(message: Message):
    await send_expiring(message)


@router.callback_query(F.data == 'expiring')
async def expiring_callback(callback: CallbackQuery):
    await callback.answer()
    await send_expiring(callback.message)
