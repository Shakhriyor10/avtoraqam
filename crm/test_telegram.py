from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock

from asgiref.sync import async_to_sync
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from crm.telegram_bot.services import notification_text, send_service_notification
from crm.telegram_bot.services import expiring_records
from crm.models import Client, ServiceRecord, Vehicle


class FakeFiles:
    def __init__(self, paths):
        self.items = [
            SimpleNamespace(file=SimpleNamespace(path=str(path), name=path.name))
            for path in paths
        ]

    def all(self):
        return self.items

    def count(self):
        return len(self.items)


def fake_service(paths):
    return SimpleNamespace(
        pk=1, days_left=5, issued_on=date(2026, 8, 1), expires_on=date(2026, 8, 19),
        client=SimpleNamespace(full_name='Клиент <Тест>', phone='+998&90'),
        vehicle=SimpleNamespace(plate_number='01<A>', make_model='Cobalt & Onix'),
        files=FakeFiles(paths), get_service_type_display=lambda: 'Страховка',
    )


class TelegramNotificationTests(SimpleTestCase):
    def test_notification_escapes_dynamic_html(self):
        text = notification_text(fake_service([]))
        self.assertIn('Клиент &lt;Тест&gt;', text)
        self.assertIn('+998&amp;90', text)
        self.assertNotIn('Клиент <Тест>', text)

    def test_multiple_files_are_grouped_and_caption_is_on_last_file(self):
        with TemporaryDirectory() as directory:
            paths = []
            for index in range(3):
                path = Path(directory) / f'document-{index}.txt'
                path.write_bytes(b'document')
                paths.append(path)
            bot = SimpleNamespace(
                send_message=AsyncMock(), send_document=AsyncMock(), send_media_group=AsyncMock()
            )
            async_to_sync(send_service_notification)(bot, -1001, fake_service(paths))
            bot.send_media_group.assert_awaited_once()
            media = bot.send_media_group.await_args.kwargs['media']
            self.assertEqual(len(media), 3)
            self.assertIsNone(media[0].caption)
            self.assertIsNone(media[1].caption)
            self.assertIn('СРОК УСЛУГИ', media[2].caption)
            self.assertEqual(media[2].parse_mode, 'HTML')
            bot.send_message.assert_not_awaited()
            bot.send_document.assert_not_awaited()


class ClosedServiceBotTests(TestCase):
    def test_closed_service_is_not_selected_for_bot(self):
        owner = Client.objects.create(full_name='Закрытый Клиент', phone='4040')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01BOT')
        ServiceRecord.objects.create(
            client=owner, vehicle=vehicle, service_type='insurance',
            issued_on=date(2026, 1, 1), expires_on=date.today(),
            closed_at=timezone.now(), closed_reason='elsewhere',
        )
        self.assertEqual(expiring_records(), [])
