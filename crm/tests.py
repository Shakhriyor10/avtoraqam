from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import Client, ClientFile, ServiceNotificationSetting, ServiceRecord, Vehicle


class CrmFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('manager', password='test-password')
        self.client.force_login(self.user)

    def test_dashboard_opens(self):
        response = self.client.get(reverse('crm:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Создать документ')
        self.assertContains(response, 'Добавлено услуг')

    def test_custom_login_and_logout(self):
        self.client.logout()
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Вход в систему')
        response = self.client.post(reverse('login'), {
            'username': 'manager', 'password': 'test-password',
        })
        self.assertRedirects(response, reverse('crm:dashboard'))
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

    def test_service_menu_opens_type_selection(self):
        response = self.client.get(reverse('crm:service_type_select'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Выберите услугу')
        self.assertContains(response, reverse('crm:service_create', args=['insurance']))
        self.assertContains(response, reverse('crm:service_create', args=['tinting']))

    def test_service_form_contains_today_as_issued_date_value(self):
        response = self.client.get(reverse('crm:service_create', args=['insurance']))
        today = timezone.localdate().isoformat()
        self.assertContains(
            response,
            f'name="issued_on" value="{today}"',
            html=False,
        )

    def test_create_service_with_new_client_and_vehicle(self):
        today = timezone.localdate()
        response = self.client.post(reverse('crm:service_create', args=['insurance']), {
            'full_name': 'Алишер Тестов', 'phone': '+998901234567',
            'plate_number': '01 A 777 AA',
            'issued_on': today, 'expires_on': today + timedelta(days=365),
            'price': '250000', 'notes': 'Тестовая запись',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Client.objects.filter(phone='+998901234567').exists())
        self.assertTrue(Vehicle.objects.filter(plate_number='01A777AA').exists())
        self.assertEqual(ServiceRecord.objects.get().service_type, 'insurance')

    def test_service_can_be_created_without_expiry_or_files(self):
        response = self.client.post(reverse('crm:service_create', args=['avtoraqam']), {
            'full_name': 'Клиент без срока', 'phone': '998901234567',
            'plate_number': '01A777AA', 'issued_on': timezone.localdate(),
            'expires_on': '', 'price': '', 'notes': '',
            'document_recipient': 'owner',
        })
        self.assertEqual(response.status_code, 302)
        service = ServiceRecord.objects.get()
        self.assertIsNone(service.expires_on)
        self.assertEqual(service.status, 'no_expiry')
        self.assertEqual(service.status_label, 'Без срока')
        self.assertFalse(service.client.files.exists())
        self.assertFalse(service.files.exists())

    def test_expiry_status(self):
        client = Client.objects.create(full_name='Клиент', phone='123')
        vehicle = Vehicle.objects.create(client=client, plate_number='01X001XX')
        service = ServiceRecord.objects.create(
            client=client, vehicle=vehicle, service_type='other',
            expires_on=timezone.localdate() - timedelta(days=1)
        )
        self.assertEqual(service.status, 'expired')

    def test_client_and_service_can_be_edited(self):
        client = Client.objects.create(full_name='Старое Имя', phone='111')
        vehicle = Vehicle.objects.create(client=client, plate_number='01OLD')
        service = ServiceRecord.objects.create(
            client=client, vehicle=vehicle, service_type='insurance',
            expires_on=timezone.localdate() + timedelta(days=10),
        )
        response = self.client.post(reverse('crm:client_edit', args=[client.pk]), {
            'full_name': 'Новое Имя', 'phone': '222', 'notes': 'Обновлено',
            'vehicles-TOTAL_FORMS': '1', 'vehicles-INITIAL_FORMS': '1',
            'vehicles-MIN_NUM_FORMS': '0', 'vehicles-MAX_NUM_FORMS': '1000',
            'vehicles-0-id': vehicle.pk, 'vehicles-0-client': client.pk,
            'vehicles-0-plate_number': '01NEW',
        })
        self.assertEqual(response.status_code, 302)
        client.refresh_from_db()
        vehicle.refresh_from_db()
        self.assertEqual(client.full_name, 'Новое Имя')
        self.assertEqual(vehicle.plate_number, '01NEW')

        new_expiry = timezone.localdate() + timedelta(days=60)
        response = self.client.post(reverse('crm:service_edit', args=[service.pk]), {
            'vehicle': vehicle.pk, 'issued_on': timezone.localdate(),
            'expires_on': new_expiry, 'price': '', 'notes': 'Продлить',
        })
        self.assertEqual(response.status_code, 302)
        service.refresh_from_db()
        self.assertEqual(service.expires_on, new_expiry)

    def test_vehicle_can_be_added_from_client_detail(self):
        client = Client.objects.create(full_name='Владелец', phone='99890')
        response = self.client.post(reverse('crm:vehicle_create', args=[client.pk]), {
            'plate_number': '01 A 123 BC',
        })
        self.assertRedirects(response, reverse('crm:client_detail', args=[client.pk]))
        vehicle = client.vehicles.get()
        self.assertEqual(vehicle.plate_number, '01A123BC')
        response = self.client.post(
            reverse('crm:vehicle_create', args=[client.pk]),
            {'plate_number': '01 B 456 DE'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertEqual(client.vehicles.count(), 2)

    def test_client_create_redirects_to_detail(self):
        response = self.client.post(reverse('crm:client_create'), {
            'full_name': 'Новый Клиент', 'phone': '+998901112233',
            'notes': 'Добавлен из списка клиентов',
        })
        client = Client.objects.get(phone='+998901112233')
        self.assertRedirects(response, reverse('crm:client_detail', args=[client.pk]))
        detail = self.client.get(response.url)
        self.assertContains(detail, 'Добавить автомобиль')

    def test_price_with_space_separators_is_saved_as_number(self):
        today = timezone.localdate()
        response = self.client.post(reverse('crm:service_create', args=['insurance']), {
            'full_name': 'Денежный Клиент', 'phone': '+998900001000',
            'plate_number': '01M100MM', 'issued_on': today,
            'expires_on': today + timedelta(days=30), 'price': '1 000 000',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ServiceRecord.objects.get(client__phone='+998900001000').price, 1000000)

    def test_vehicle_selection_automatically_uses_its_client(self):
        owner = Client.objects.create(full_name='Владелец машины', phone='+998901010101')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01AUTO01')
        today = timezone.localdate()
        response = self.client.post(reverse('crm:service_create', args=['tinting']), {
            'existing_vehicle': vehicle.pk,
            'issued_on': today,
            'expires_on': today + timedelta(days=30),
        })
        self.assertEqual(response.status_code, 302)
        service = ServiceRecord.objects.get()
        self.assertEqual(service.client, owner)
        self.assertEqual(service.vehicle, vehicle)

    def test_new_same_service_renews_old_warning(self):
        owner = Client.objects.create(full_name='Клиент Продление', phone='+998909999999')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01REN01')
        today = timezone.localdate()
        old_service = ServiceRecord.objects.create(
            client=owner, vehicle=vehicle, service_type='insurance',
            issued_on=today - timedelta(days=365), expires_on=today + timedelta(days=2),
        )
        response = self.client.post(reverse('crm:service_create', args=['insurance']), {
            'existing_client': owner.pk, 'existing_vehicle': vehicle.pk,
            'issued_on': today, 'expires_on': today + timedelta(days=365),
        })
        self.assertEqual(response.status_code, 302)
        old_service.refresh_from_db()
        self.assertIsNotNone(old_service.renewed_by_id)
        self.assertEqual(old_service.status, 'renewed')
        dashboard = self.client.get(reverse('crm:dashboard'), {'status': 'warning'})
        self.assertEqual(dashboard.context['warning_count'], 0)
        self.assertNotIn(old_service, list(dashboard.context['services']))

    def test_renew_link_prefills_client_and_vehicle(self):
        owner = Client.objects.create(full_name='Клиент продления', phone='2020')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01RENEW')
        service = ServiceRecord.objects.create(
            client=owner, vehicle=vehicle, service_type='insurance',
            issued_on=timezone.localdate() - timedelta(days=365),
            expires_on=timezone.localdate() + timedelta(days=2),
        )
        renew_url = (
            reverse('crm:service_create', args=['insurance']) + f'?renew={service.pk}'
        )
        dashboard = self.client.get(reverse('crm:dashboard'))
        self.assertContains(dashboard, renew_url.replace('&', '&amp;'))
        response = self.client.get(renew_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['renewing_service'], service)
        self.assertEqual(response.context['form'].initial['existing_client'], owner)
        self.assertEqual(response.context['form'].initial['existing_vehicle'], vehicle)
        self.assertEqual(response.context['form'].initial['issued_on'], timezone.localdate())

    def test_warning_can_be_closed_when_client_uses_another_provider(self):
        owner = Client.objects.create(full_name='Клиент Другой Офис', phone='3030')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01CLOSE')
        service = ServiceRecord.objects.create(
            client=owner, vehicle=vehicle, service_type='insurance',
            issued_on=timezone.localdate() - timedelta(days=100),
            expires_on=timezone.localdate() + timedelta(days=2),
        )
        self.assertEqual(service.status, 'warning')
        response = self.client.post(
            reverse('crm:service_close', args=[service.pk]),
            {'reason': 'elsewhere'},
        )
        self.assertRedirects(response, reverse('crm:client_detail', args=[owner.pk]))
        service.refresh_from_db()
        self.assertEqual(service.status, 'closed')
        self.assertEqual(service.closed_reason, 'elsewhere')
        self.assertEqual(service.closed_by, self.user)
        dashboard = self.client.get(reverse('crm:dashboard'))
        self.assertEqual(dashboard.context['warning_count'], 0)
        self.assertNotIn(service, list(dashboard.context['services']))
        default_results = self.client.get(reverse('crm:service_search')).json()['results']
        self.assertEqual(default_results, [])
        closed_results = self.client.get(
            reverse('crm:service_search'), {'status': 'closed'}
        ).json()['results']
        self.assertEqual([item['status'] for item in closed_results], ['closed'])
        searched_closed = self.client.get(
            reverse('crm:service_search'), {'q': owner.full_name}
        ).json()['results']
        self.assertEqual([item['status'] for item in searched_closed], ['closed'])
        searched_by_status = self.client.get(
            reverse('crm:service_search'), {'q': 'Закрытые'}
        ).json()['results']
        self.assertEqual([item['status'] for item in searched_by_status], ['closed'])
        warning_results = self.client.get(
            reverse('crm:service_search'), {'status': 'warning'}
        ).json()['results']
        self.assertEqual(warning_results, [])

    def test_warning_can_be_closed_with_ajax_without_redirect(self):
        owner = Client.objects.create(full_name='AJAX клиент', phone='4040')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01AJAX')
        service = ServiceRecord.objects.create(
            client=owner, vehicle=vehicle, service_type='insurance',
            issued_on=timezone.localdate() - timedelta(days=100),
            expires_on=timezone.localdate() + timedelta(days=2),
        )
        response = self.client.post(
            reverse('crm:service_close', args=[service.pk]),
            {'reason': 'declined'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'ok': True,
            'status': 'closed',
            'status_label': 'Закрыта',
            'reason_label': 'Клиент отказался',
        })
        service.refresh_from_db()
        self.assertEqual(service.status, 'closed')
        self.assertEqual(service.closed_reason, 'declined')

    def test_service_delete_requires_current_user_password(self):
        owner = Client.objects.create(full_name='Клиент удаления', phone='5050')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01DELETE')
        service = ServiceRecord.objects.create(
            client=owner, vehicle=vehicle, service_type='other',
            issued_on=timezone.localdate(),
            expires_on=timezone.localdate() + timedelta(days=100),
        )
        delete_url = reverse('crm:service_delete', args=[service.pk])
        dashboard = self.client.get(reverse('crm:dashboard'))
        self.assertContains(dashboard, delete_url)
        client_detail = self.client.get(reverse('crm:client_detail', args=[owner.pk]))
        self.assertContains(client_detail, delete_url)

        response = self.client.post(
            delete_url, {'password': 'wrong-password'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(ServiceRecord.objects.filter(pk=service.pk).exists())

        response = self.client.post(
            delete_url, {'password': 'test-password'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'ok': True, 'status': 'active'})
        self.assertFalse(ServiceRecord.objects.filter(pk=service.pk).exists())

    def test_client_delete_requires_password_and_removes_related_data(self):
        owner = Client.objects.create(full_name='Удаляемый клиент', phone='6060')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01CASCADE')
        service = ServiceRecord.objects.create(
            client=owner, vehicle=vehicle, service_type='insurance',
            issued_on=timezone.localdate(),
            expires_on=timezone.localdate() + timedelta(days=100),
        )
        delete_url = reverse('crm:client_delete', args=[owner.pk])
        self.assertContains(self.client.get(reverse('crm:client_list')), delete_url)
        self.assertContains(
            self.client.get(reverse('crm:client_detail', args=[owner.pk])), delete_url
        )
        search_result = self.client.get(
            reverse('crm:client_search'), {'q': 'Удаляемый'}
        ).json()['results'][0]
        self.assertEqual(search_result['delete_url'], delete_url)

        response = self.client.post(
            delete_url, {'password': 'wrong-password'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Client.objects.filter(pk=owner.pk).exists())

        response = self.client.post(
            delete_url, {'password': 'test-password'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['redirect_url'], reverse('crm:client_list'))
        self.assertFalse(Client.objects.filter(pk=owner.pk).exists())
        self.assertFalse(Vehicle.objects.filter(pk=vehicle.pk).exists())
        self.assertFalse(ServiceRecord.objects.filter(pk=service.pk).exists())

    def test_client_edit_can_add_multiple_vehicles_at_once(self):
        owner = Client.objects.create(full_name='Несколько авто', phone='7070')
        edit_url = reverse('crm:client_edit', args=[owner.pk])
        self.assertContains(self.client.get(edit_url), 'id="add-vehicle-row"')
        response = self.client.post(edit_url, {
            'full_name': owner.full_name,
            'phone': owner.phone,
            'notes': '',
            'vehicles-TOTAL_FORMS': '3',
            'vehicles-INITIAL_FORMS': '0',
            'vehicles-MIN_NUM_FORMS': '0',
            'vehicles-MAX_NUM_FORMS': '1000',
            'vehicles-0-plate_number': '01AAA01',
            'vehicles-1-plate_number': '01BBB02',
            'vehicles-2-plate_number': '01CCC03',
        })
        self.assertRedirects(response, reverse('crm:client_detail', args=[owner.pk]))
        self.assertEqual(owner.vehicles.count(), 3)

    def test_dashboard_paginates_50_but_searches_all_services(self):
        owner = Client.objects.create(full_name='Массовый Клиент', phone='100')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01MASS')
        today = timezone.localdate()
        ServiceRecord.objects.bulk_create([
            ServiceRecord(
                client=owner, vehicle=vehicle, service_type='other',
                issued_on=today, expires_on=today + timedelta(days=number + 1),
                notes=f'Запись {number}',
            ) for number in range(55)
        ])
        special = Client.objects.create(full_name='Уникальный Поиск', phone='999')
        special_vehicle = Vehicle.objects.create(client=special, plate_number='01UNIQUE')
        ServiceRecord.objects.create(
            client=special, vehicle=special_vehicle, service_type='insurance',
            issued_on=today, expires_on=today + timedelta(days=1000),
        )
        dashboard = self.client.get(reverse('crm:dashboard'))
        self.assertEqual(len(dashboard.context['services']), 50)
        response = self.client.get(reverse('crm:service_search'), {'q': 'Уникальный'})
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['client'], 'Уникальный Поиск')
        response = self.client.get(reverse('crm:service_search'), {
            'date_to': (today + timedelta(days=2000)).isoformat(),
        })
        self.assertGreater(len(response.json()['results']), 50)

    def test_dashboard_statuses_do_not_create_query_per_service(self):
        owner = Client.objects.create(full_name='Проверка запросов', phone='1111')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01QUERY')
        today = timezone.localdate()
        ServiceRecord.objects.bulk_create([
            ServiceRecord(
                client=owner, vehicle=vehicle, service_type='insurance',
                issued_on=today, expires_on=today + timedelta(days=number + 1),
            )
            for number in range(20)
        ])
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(reverse('crm:dashboard'))
            self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(captured), 20)

    def test_service_type_has_individual_warning_days(self):
        ServiceNotificationSetting.objects.create(service_type='insurance', warning_days=10)
        owner = Client.objects.create(full_name='Настройка Срока', phone='1010')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01DAYS')
        today = timezone.localdate()
        insurance = ServiceRecord.objects.create(
            client=owner, vehicle=vehicle, service_type='insurance',
            issued_on=today, expires_on=today + timedelta(days=11),
        )
        self.assertEqual(insurance.status, 'active')
        insurance.expires_on = today + timedelta(days=10)
        insurance.save(update_fields=['expires_on'])
        self.assertEqual(insurance.status, 'warning')
        response = self.client.post(reverse('crm:notification_settings'), {
            'days_avtoraqam': '15', 'days_insurance': '7', 'days_tinting': '12',
            'days_power_of_attorney': '20', 'days_other': '5',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ServiceNotificationSetting.get_warning_days('insurance'), 7)

    def test_date_range_recalculates_dashboard_stats(self):
        today = timezone.localdate()
        first = Client.objects.create(full_name='В периоде', phone='1')
        first_car = Vehicle.objects.create(client=first, plate_number='01IN')
        ServiceRecord.objects.create(
            client=first, vehicle=first_car, service_type='insurance',
            issued_on=today, expires_on=today + timedelta(days=5),
        )
        second = Client.objects.create(full_name='Вне периода', phone='2')
        second_car = Vehicle.objects.create(client=second, plate_number='01OUT')
        second_service = ServiceRecord.objects.create(
            client=second, vehicle=second_car, service_type='tinting',
            issued_on=today, expires_on=today + timedelta(days=100),
        )
        old_date = timezone.now() - timedelta(days=20)
        Client.objects.filter(pk=second.pk).update(created_at=old_date)
        Vehicle.objects.filter(pk=second_car.pk).update(created_at=old_date)
        ServiceRecord.objects.filter(pk=second_service.pk).update(created_at=old_date)
        response = self.client.get(reverse('crm:service_search'), {
            'date_from': today.isoformat(),
            'date_to': (today + timedelta(days=10)).isoformat(),
        })
        stats = response.json()['stats']
        self.assertEqual(stats['client_count'], 1)
        self.assertEqual(stats['vehicle_count'], 1)
        self.assertEqual(stats['service_count'], 1)
        self.assertEqual(stats['warning_count'], 1)

    def test_client_list_paginates_but_searches_full_database(self):
        Client.objects.bulk_create([
            Client(full_name=f'Обычный Клиент {number}', phone=f'100{number}')
            for number in range(55)
        ])
        special = Client.objects.create(full_name='Особенный Клиент', phone='777777')
        response = self.client.get(reverse('crm:client_list'))
        self.assertEqual(len(response.context['clients']), 50)
        self.assertEqual(response.context['page_obj'].paginator.num_pages, 2)
        response = self.client.get(reverse('crm:client_list'), {'q': 'Особенный'})
        self.assertEqual(len(response.context['clients']), 1)
        self.assertEqual(response.context['clients'][0], special)
        response = self.client.get(reverse('crm:client_search'), {'q': 'Особенный'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'][0]['name'], 'Особенный Клиент')

    def test_client_vehicles_endpoint_returns_all_cars(self):
        owner = Client.objects.create(full_name='Два Авто', phone='2020')
        Vehicle.objects.create(client=owner, plate_number='01ONE')
        Vehicle.objects.create(client=owner, plate_number='01TWO')
        response = self.client.get(reverse('crm:client_vehicles', args=[owner.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['vehicles']), 2)

    def test_multiple_client_and_service_files(self):
        today = timezone.localdate()
        passports = [
            SimpleUploadedFile(f'passport-{number}.txt', b'passport')
            for number in range(3)
        ]
        documents = [
            SimpleUploadedFile(f'document-{number}.txt', b'document')
            for number in range(3)
        ]
        response = self.client.post(reverse('crm:service_create', args=['tinting']), {
            'full_name': 'Файловый Клиент', 'phone': '+998900000001',
            'plate_number': '01 B 111 BB',
            'issued_on': today, 'expires_on': today + timedelta(days=30),
            'passport_files': passports, 'service_files': documents,
        })
        self.assertEqual(response.status_code, 302)
        client = Client.objects.get(phone='+998900000001')
        self.assertEqual(client.files.count(), 3)
        self.assertEqual(client.services.get().files.count(), 3)

    def test_rejects_more_than_three_files(self):
        today = timezone.localdate()
        passports = [
            SimpleUploadedFile(f'passport-{number}.txt', b'passport')
            for number in range(4)
        ]
        response = self.client.post(reverse('crm:service_create', args=['insurance']), {
            'full_name': 'Клиент Четыре Файла', 'phone': '+998900000004',
            'plate_number': '01 C 444 CC', 'issued_on': today,
            'expires_on': today + timedelta(days=30), 'passport_files': passports,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Можно прикрепить не более 3 файлов')
        self.assertFalse(Client.objects.filter(phone='+998900000004').exists())

    def test_invalid_date_filters_do_not_crash(self):
        response = self.client.get(reverse('crm:dashboard'), {
            'date_from': 'not-a-date', 'date_to': '2026-99-99',
        })
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('crm:service_search'), {
            'date_from': 'not-a-date', 'date_to': '2026-99-99',
        })
        self.assertEqual(response.status_code, 200)

    def test_notification_settings_are_not_partially_saved(self):
        ServiceNotificationSetting.objects.create(
            service_type='insurance', warning_days=10
        )
        response = self.client.post(reverse('crm:notification_settings'), {
            'days_insurance': '7',
            'days_tinting': 'invalid',
            'days_power_of_attorney': '20',
            'days_other': '5',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ServiceNotificationSetting.get_warning_days('insurance'), 10
        )
        self.assertFalse(
            ServiceNotificationSetting.objects.filter(service_type='other').exists()
        )

    def test_vehicle_with_services_cannot_be_deleted_by_forged_post(self):
        owner = Client.objects.create(full_name='Защищённый автомобиль', phone='8080')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01SAFE')
        service = ServiceRecord.objects.create(
            client=owner, vehicle=vehicle, service_type='insurance',
            issued_on=timezone.localdate(),
            expires_on=timezone.localdate() + timedelta(days=100),
        )
        response = self.client.post(reverse('crm:client_edit', args=[owner.pk]), {
            'full_name': owner.full_name,
            'phone': owner.phone,
            'notes': '',
            'vehicles-TOTAL_FORMS': '1',
            'vehicles-INITIAL_FORMS': '1',
            'vehicles-MIN_NUM_FORMS': '0',
            'vehicles-MAX_NUM_FORMS': '1000',
            'vehicles-0-id': vehicle.pk,
            'vehicles-0-client': owner.pk,
            'vehicles-0-plate_number': vehicle.plate_number,
            'vehicles-0-DELETE': 'on',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Нельзя удалить автомобиль')
        self.assertTrue(Vehicle.objects.filter(pk=vehicle.pk).exists())
        self.assertTrue(ServiceRecord.objects.filter(pk=service.pk).exists())

    def test_existing_client_cannot_exceed_three_passport_files(self):
        owner = Client.objects.create(full_name='Три файла', phone='9090')
        for number in range(3):
            ClientFile.objects.create(
                client=owner,
                file=SimpleUploadedFile(f'passport-{number}.txt', b'passport'),
            )
        vehicle = Vehicle.objects.create(client=owner, plate_number='01FILES')
        response = self.client.post(
            reverse('crm:service_create', args=['insurance']),
            {
                'existing_client': owner.pk,
                'existing_vehicle': vehicle.pk,
                'issued_on': timezone.localdate(),
                'expires_on': timezone.localdate() + timedelta(days=30),
                'passport_files': SimpleUploadedFile('extra.txt', b'extra'),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(owner.files.count(), 3)
        self.assertFalse(owner.services.exists())

    def test_multiple_service_types_can_be_created_in_one_request(self):
        owner = Client.objects.create(full_name='Мульти клиент', phone='998900000001')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01MULTI')
        today = timezone.localdate()
        response = self.client.post(reverse('crm:service_create', args=['insurance']), {
            'existing_client': owner.pk,
            'existing_vehicle': vehicle.pk,
            'issued_on': today,
            'expires_on': today + timedelta(days=365),
            'price': '500 000',
            'additional-TOTAL_FORMS': '3',
            'additional-INITIAL_FORMS': '3',
            'additional-MIN_NUM_FORMS': '0',
            'additional-MAX_NUM_FORMS': '1000',
            'additional-0-service_type': 'tinting',
            'additional-0-enabled': 'on',
            'additional-0-expires_on': today + timedelta(days=180),
            'additional-0-price': '300 000',
            'additional-1-service_type': 'power_of_attorney',
            'additional-2-service_type': 'other',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(owner.services.count(), 2)
        self.assertEqual(
            set(owner.services.values_list('service_type', flat=True)),
            {'insurance', 'tinting'},
        )
        self.assertEqual(owner.services.get(service_type='tinting').price, 300000)

    def test_client_search_data_contains_vehicle_plate(self):
        owner = Client.objects.create(full_name='Поиск по номеру', phone='998900000002')
        vehicle = Vehicle.objects.create(client=owner, plate_number='01SEARCH')
        response = self.client.get(reverse('crm:service_create', args=['insurance']))
        self.assertContains(response, 'client-vehicles')
        self.assertContains(response, vehicle.plate_number)
        self.assertNotContains(response, 'id_make_model')
