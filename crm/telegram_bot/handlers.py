from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from asgiref.sync import sync_to_async
from django.conf import settings

from .services import dashboard_counts, expiring_records

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


EXPIRING_PAGE_SIZE = 10


def expiring_page_markup(page, page_count):
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text='⬅️ Назад', callback_data=f'show_expiring:{page - 1}'))
    buttons.append(InlineKeyboardButton(text=f'{page + 1}/{page_count}', callback_data='expiring_page_info'))
    if page + 1 < page_count:
        buttons.append(InlineKeyboardButton(text='Далее ➡️', callback_data=f'show_expiring:{page + 1}'))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def expiring_page_text(records, page, page_count):
    lines = [
        f'⚠️ <b>Истекают или уже просрочены: {len(records)}</b>',
        f'Страница {page + 1} из {page_count}. Показано до {EXPIRING_PAGE_SIZE} услуг:',
        '',
    ]
    start = page * EXPIRING_PAGE_SIZE
    for index, service in enumerate(records[start:start + EXPIRING_PAGE_SIZE], start=start + 1):
        remaining = (
            f'осталось {service.days_left} дн.' if service.days_left >= 0
            else f'просрочено на {abs(service.days_left)} дн.'
        )
        lines.extend([
            f'<b>{index}. {escape(service.get_service_type_display())}</b>',
            f'Клиент: {escape(service.client.full_name)} · {escape(service.client.phone)}',
            f'Авто: {escape(service.vehicle.plate_number)} · до {service.expires_on:%d.%m.%Y} · {remaining}',
            '',
        ])
    return '\n'.join(lines).rstrip()


async def send_expiring(target, page=0):
    records = await sync_to_async(expiring_records, thread_sensitive=True)()
    if not records:
        await target.answer('✅ Услуг, требующих внимания, сейчас нет.', reply_markup=menu())
        return
    page_count = (len(records) + EXPIRING_PAGE_SIZE - 1) // EXPIRING_PAGE_SIZE
    page = max(0, min(page, page_count - 1))
    await target.answer(
        expiring_page_text(records, page, page_count), parse_mode='HTML',
        reply_markup=expiring_page_markup(page, page_count),
    )


@router.message(Command('expiring'))
async def expiring_command(message: Message):
    await send_expiring(message)


@router.callback_query(F.data == 'expiring')
async def expiring_callback(callback: CallbackQuery):
    await callback.answer()
    await send_expiring(callback.message)


@router.callback_query(F.data == 'show_expiring')
async def show_expiring_callback(callback: CallbackQuery):
    await callback.answer()
    await show_expiring_page(callback, 0)


@router.callback_query(F.data.startswith('show_expiring:'))
async def expiring_page_callback(callback: CallbackQuery):
    await callback.answer()
    try:
        page = int(callback.data.partition(':')[2])
    except (TypeError, ValueError):
        page = 0
    await show_expiring_page(callback, page)


async def show_expiring_page(callback, page):
    records = await sync_to_async(expiring_records, thread_sensitive=True)()
    if not records:
        await callback.message.edit_text('✅ Услуг, требующих внимания, сейчас нет.')
        return
    page_count = (len(records) + EXPIRING_PAGE_SIZE - 1) // EXPIRING_PAGE_SIZE
    page = max(0, min(page, page_count - 1))
    await callback.message.edit_text(
        expiring_page_text(records, page, page_count), parse_mode='HTML',
        reply_markup=expiring_page_markup(page, page_count),
    )


@router.callback_query(F.data == 'expiring_page_info')
async def expiring_page_info_callback(callback: CallbackQuery):
    await callback.answer()
