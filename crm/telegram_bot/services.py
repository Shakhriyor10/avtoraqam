import logging
from html import escape
from pathlib import Path
from datetime import timedelta

from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaDocument
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db import close_old_connections

from crm.models import Client, ServiceNotificationSetting, ServiceRecord, Vehicle


def warning_days_map():
    return ServiceNotificationSetting.warning_days_map()


def expiring_records():
    close_old_connections()
    today = timezone.localdate()
    warning_days = warning_days_map()
    records = []
    queryset = ServiceRecord.objects.select_related('client', 'vehicle').prefetch_related('files').filter(
        renewed_by__isnull=True, closed_at__isnull=True,
        expires_on__lte=today + timedelta(days=365)
    ).order_by('expires_on')
    for service in queryset:
        if service.days_left <= warning_days[service.service_type]:
            records.append(service)
    return records


def dashboard_counts():
    close_old_connections()
    services = ServiceRecord.objects.filter(renewed_by__isnull=True, closed_at__isnull=True)
    warning_days = warning_days_map()
    warning = expired = 0
    for service in services:
        if service.days_left < 0:
            expired += 1
        elif service.days_left <= warning_days[service.service_type]:
            warning += 1
    return {
        'clients': Client.objects.count(), 'vehicles': Vehicle.objects.count(),
        'services': ServiceRecord.objects.count(), 'warning': warning, 'expired': expired,
    }


def notification_text(service):
    remaining = (
        f'осталось {service.days_left} дн.' if service.days_left >= 0
        else f'просрочено на {abs(service.days_left)} дн.'
    )
    service_name = escape(service.get_service_type_display())
    client_name = escape(service.client.full_name)
    phone = escape(service.client.phone)
    plate_number = escape(service.vehicle.plate_number)
    vehicle_name = ''
    return (
        '⚠️ <b>СРОК УСЛУГИ ПОДХОДИТ К КОНЦУ</b>\n\n'
        f'<b>Услуга:</b> {service_name}\n'
        f'<b>Клиент:</b> {client_name}\n'
        f'<b>Телефон:</b> {phone}\n'
        f'<b>Автомобиль:</b> {plate_number}{vehicle_name}\n'
        f'<b>Дата оформления:</b> {service.issued_on:%d.%m.%Y}\n'
        f'<b>Действует до:</b> {service.expires_on:%d.%m.%Y}\n'
        f'<b>Статус:</b> {remaining}\n'
        f'<b>Файлов:</b> {service.files.count()}\n\n'
        '📞 Свяжитесь с клиентом для продления услуги.'
    )


async def send_service_notification(bot: Bot, chat_id: int | str, service, include_files=True):
    text = notification_text(service)
    attachments = list(service.files.all()) if include_files else []
    available_files = []
    missing_files = []
    for attached in attachments:
        try:
            path = Path(attached.file.path)
            if path.is_file():
                available_files.append(path)
            else:
                missing_files.append(attached.file.name)
        except (OSError, ValueError):
            missing_files.append(attached.file.name)

    if not available_files:
        await bot.send_message(chat_id, text, parse_mode='HTML')
    elif len(available_files) == 1:
        await bot.send_document(
            chat_id, FSInputFile(available_files[0]), caption=text, parse_mode='HTML'
        )
    else:
        grouped_files = available_files[:10]
        last_index = len(grouped_files) - 1
        media = [
            InputMediaDocument(
                media=FSInputFile(path),
                caption=text if index == last_index else None,
                parse_mode='HTML' if index == last_index else None,
            )
            for index, path in enumerate(grouped_files)
        ]
        await bot.send_media_group(chat_id, media=media)

    if missing_files:
        await bot.send_message(
            chat_id,
            'Не удалось открыть файлы:\n' + '\n'.join(f'• {name}' for name in missing_files),
        )


async def send_due_notifications(bot: Bot, chat_id: int | str):
    records = await sync_to_async(expiring_records, thread_sensitive=True)()
    sent = 0
    today = timezone.localdate()
    for service in records:
        if service.notified_at and timezone.localtime(service.notified_at).date() >= today:
            continue
        try:
            await send_service_notification(bot, chat_id, service)
            service.notified_at = timezone.now()
            await sync_to_async(service.save, thread_sensitive=True)(update_fields=['notified_at'])
            sent += 1
        except Exception:
            logging.exception('Не удалось отправить уведомление для услуги id=%s', service.pk)
    return sent
