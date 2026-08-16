from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.core.paginator import Paginator
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from .forms import (
    AdditionalServiceFormSet, ClientForm, ServiceCreateForm, ServiceEditForm, StaffUserCreationForm,
    VehicleForm, VehicleFormSet,
)
from .models import Client, ClientFile, ServiceFile, ServiceNotificationSetting, ServiceRecord, Vehicle


def notification_days_map():
    return ServiceNotificationSetting.warning_days_map()


def attach_warning_days(records, days_map=None):
    days_map = days_map or notification_days_map()
    for record in records:
        record._warning_days = days_map[record.service_type]
    return records


def valid_date(value):
    if not value:
        return None
    try:
        return parse_date(value)
    except ValueError:
        return None


def warning_query(today, days_map=None):
    days_map = days_map or notification_days_map()
    query = Q(pk__in=[])
    for service_type, _label in ServiceRecord.ServiceType.choices:
        days = days_map[service_type]
        query |= Q(service_type=service_type, expires_on__range=(today, today + timedelta(days=days)))
    return query


def dashboard_stats(date_from='', date_to='', days_map=None):
    today = timezone.localdate()
    clients = Client.objects.all()
    vehicles = Vehicle.objects.all()
    created_services = ServiceRecord.objects.all()
    expiring_services = ServiceRecord.objects.filter(
        renewed_by__isnull=True, closed_at__isnull=True
    )
    date_from = valid_date(date_from)
    date_to = valid_date(date_to)
    revenue_services = ServiceRecord.objects.all()
    if not date_from and not date_to:
        revenue_services = revenue_services.filter(created_at__date=today)
    if date_from:
        clients = clients.filter(created_at__date__gte=date_from)
        vehicles = vehicles.filter(created_at__date__gte=date_from)
        created_services = created_services.filter(created_at__date__gte=date_from)
        expiring_services = expiring_services.filter(created_at__date__gte=date_from)
        revenue_services = revenue_services.filter(created_at__date__gte=date_from)
    if date_to:
        clients = clients.filter(created_at__date__lte=date_to)
        vehicles = vehicles.filter(created_at__date__lte=date_to)
        created_services = created_services.filter(created_at__date__lte=date_to)
        expiring_services = expiring_services.filter(created_at__date__lte=date_to)
        revenue_services = revenue_services.filter(created_at__date__lte=date_to)
    return {
        'client_count': clients.count(),
        'vehicle_count': vehicles.count(),
        'service_count': created_services.count(),
        'warning_count': expiring_services.filter(
            warning_query(today, days_map)
        ).count(),
        'expired_count': expiring_services.filter(expires_on__lt=today).count(),
        'revenue_total': revenue_services.aggregate(total=Sum('price'))['total'] or 0,
    }


@login_required
def dashboard(request):
    days_map = notification_days_map()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    service_list = filter_services(request, days_map)
    search_query = request.GET.get('q', '').strip()
    if search_query:
        page_obj = None
        displayed_services = list(service_list)
    else:
        page_obj = Paginator(service_list, 50).get_page(request.GET.get('page'))
        displayed_services = list(page_obj.object_list)
    attach_warning_days(displayed_services, days_map)
    context = {
        **dashboard_stats(date_from, date_to, days_map),
        'services': displayed_services,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': request.GET.get('status', ''),
        'date_from': date_from,
        'date_to': date_to,
        'service_types': ServiceRecord.ServiceType.choices,
    }
    return render(request, 'crm/dashboard.html', context)


def filter_services(request, days_map=None):
    today = timezone.localdate()
    queryset = ServiceRecord.objects.select_related('client', 'vehicle').order_by('expires_on')
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    date_from = valid_date(request.GET.get('date_from', ''))
    date_to = valid_date(request.GET.get('date_to', ''))
    days_map = days_map or notification_days_map()
    if query:
        normalized_query = query.lower()
        service_values = [
            value for value, label in ServiceRecord.ServiceType.choices
            if normalized_query in label.lower()
        ]
        search_query = (
            Q(client__full_name__icontains=query) | Q(client__phone__icontains=query) |
            Q(vehicle__plate_number__icontains=query) | Q(service_type__in=service_values)
        )
        if normalized_query in {'закрыта', 'закрытые', 'закрыт', 'закрыто'}:
            search_query |= Q(closed_at__isnull=False)
        queryset = queryset.filter(search_query)
    if status == 'warning':
        queryset = queryset.filter(
            renewed_by__isnull=True, closed_at__isnull=True
        ).filter(warning_query(today, days_map))
    elif status == 'expired':
        queryset = queryset.filter(
            renewed_by__isnull=True, closed_at__isnull=True, expires_on__lt=today
        )
    elif status == 'active':
        queryset = queryset.filter(
            renewed_by__isnull=True, closed_at__isnull=True
        ).exclude(expires_on__lte=today).exclude(warning_query(today, days_map))
    elif status == 'renewed':
        queryset = queryset.filter(renewed_by__isnull=False)
    elif status == 'closed':
        queryset = queryset.filter(closed_at__isnull=False)
    elif not query:
        queryset = queryset.filter(closed_at__isnull=True)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    return queryset


@login_required
@transaction.atomic
def notification_settings(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    rows = []
    if request.method == 'POST':
        valid = True
        pending = {}
        for service_type, label in ServiceRecord.ServiceType.choices:
            raw_value = request.POST.get(f'days_{service_type}', '').strip()
            try:
                days = int(raw_value)
                if not 0 <= days <= 365:
                    raise ValueError
            except ValueError:
                messages.error(request, f'{label}: укажите число от 0 до 365.')
                valid = False
                continue
            pending[service_type] = days
        if valid:
            for service_type, days in pending.items():
                ServiceNotificationSetting.objects.update_or_create(
                    service_type=service_type, defaults={'warning_days': days}
                )
            messages.success(request, 'Настройки уведомлений сохранены.')
            return redirect('crm:notification_settings')
    for service_type, label in ServiceRecord.ServiceType.choices:
        rows.append({
            'value': service_type, 'label': label,
            'days': ServiceNotificationSetting.get_warning_days(service_type),
        })
    return render(request, 'crm/notification_settings.html', {
        'settings_rows': rows,
        'user_form': StaffUserCreationForm(),
        'managed_users': get_user_model().objects.filter(is_superuser=False).order_by('username'),
    })


@login_required
@transaction.atomic
def user_create(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    form = StaffUserCreationForm(request.POST)
    if form.is_valid():
        user = form.save()
        messages.success(request, f'Пользователь {user.username} создан.')
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect('crm:notification_settings')


@login_required
@transaction.atomic
def user_toggle_active(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    user = get_object_or_404(get_user_model(), pk=pk, is_superuser=False)
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    messages.success(request, f'Пользователь {user.username} обновлён.')
    return redirect('crm:notification_settings')


@login_required
def service_search(request):
    days_map = notification_days_map()
    services = filter_services(request, days_map)
    filtered = any([
        request.GET.get('q', '').strip(), request.GET.get('status', ''),
        request.GET.get('date_from', ''), request.GET.get('date_to', ''),
    ])
    if not filtered:
        services = services[:50]
    services = attach_warning_days(list(services), days_map)
    return JsonResponse({
        'results': [{
            'client': item.client.full_name,
            'phone': item.client.phone,
            'client_url': reverse('crm:client_detail', args=[item.client_id]),
            'vehicle': item.vehicle.plate_number,
            'service': item.get_service_type_display(),
            'expires_on': item.expires_on.strftime('%d.%m.%Y') if item.expires_on else 'Без срока',
            'status': item.status,
            'status_label': item.status_label,
            'close_url': reverse('crm:service_close', args=[item.pk]) + '?next=dashboard',
            'renew_url': reverse('crm:service_create', args=[item.service_type]) + f'?renew={item.pk}',
            'delete_url': reverse('crm:service_delete', args=[item.pk]),
            'deletable': request.user.is_superuser,
            'closable': item.status in {'warning', 'expired'},
        } for item in services],
        'filtered': filtered,
        'stats': dashboard_stats(
            request.GET.get('date_from', ''), request.GET.get('date_to', ''), days_map
        ),
    })


@login_required
def client_list(request):
    query = request.GET.get('q', '').strip()
    clients = Client.objects.annotate(vehicle_count=Count('vehicles', distinct=True)).order_by('-created_at', '-pk')
    if query:
        clients = clients.filter(
            Q(full_name__icontains=query) | Q(phone__icontains=query) |
            Q(vehicles__plate_number__icontains=query)
        ).distinct()
    page_obj = Paginator(clients, 50).get_page(request.GET.get('page'))
    return render(request, 'crm/client_list.html', {
        'clients': page_obj.object_list, 'page_obj': page_obj, 'query': query,
    })


@login_required
def client_search(request):
    query = request.GET.get('q', '').strip()
    clients = Client.objects.annotate(
        vehicle_count=Count('vehicles', distinct=True)
    ).order_by('-created_at', '-pk')
    if query:
        clients = clients.filter(
            Q(full_name__icontains=query) | Q(phone__icontains=query) |
            Q(vehicles__plate_number__icontains=query)
        ).distinct()
    else:
        clients = clients[:50]
    return JsonResponse({'results': [{
        'name': client.full_name,
        'phone': client.phone,
        'vehicle_count': client.vehicle_count,
        'created_at': client.created_at.strftime('%d.%m.%Y'),
        'url': reverse('crm:client_detail', args=[client.pk]),
        'vehicles_url': reverse('crm:client_vehicles', args=[client.pk]),
        'delete_url': reverse('crm:client_delete', args=[client.pk]),
        'deletable': request.user.is_superuser,
    } for client in clients]})


@login_required
def client_vehicles(request, pk):
    client = get_object_or_404(Client, pk=pk)
    return JsonResponse({
        'client': client.full_name,
        'vehicles': [{
            'plate_number': vehicle.plate_number,
        } for vehicle in client.vehicles.order_by('-created_at')],
    })


@login_required
@transaction.atomic
def client_create(request):
    form = ClientForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        client = form.save()
        for uploaded in request.FILES.getlist('passport_files'):
            ClientFile.objects.create(client=client, file=uploaded)
        messages.success(request, 'Клиент добавлен. Теперь можно добавить его автомобиль.')
        return redirect('crm:client_detail', pk=client.pk)
    return render(request, 'crm/client_create.html', {'form': form})


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client.objects.prefetch_related('files', 'vehicles'), pk=pk)
    services = attach_warning_days(list(
        client.services.select_related('vehicle').prefetch_related('files')
    ))
    return render(request, 'crm/client_detail.html', {'client': client, 'services': services})


@login_required
@transaction.atomic
def client_delete(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    client = get_object_or_404(Client, pk=pk)
    if not request.user.check_password(request.POST.get('password', '')):
        return JsonResponse({
            'ok': False, 'error': 'Неверный пароль. Клиент не удалён.'
        }, status=400)
    client.delete()
    return JsonResponse({'ok': True, 'redirect_url': reverse('crm:client_list')})


@login_required
@transaction.atomic
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = ClientForm(request.POST or None, request.FILES or None, instance=client)
    vehicles = VehicleFormSet(request.POST or None, instance=client, prefix='vehicles')
    if request.method == 'POST' and form.is_valid() and vehicles.is_valid():
        new_files = request.FILES.getlist('passport_files')
        if client.files.count() + len(new_files) > 3:
            form.add_error('passport_files', 'У клиента может быть не более 3 файлов. Удалите старый файл или добавьте меньше новых.')
        else:
            form.save()
            vehicles.save()
            for uploaded in new_files:
                ClientFile.objects.create(client=client, file=uploaded)
            messages.success(request, 'Данные клиента успешно обновлены.')
            return redirect('crm:client_detail', pk=client.pk)
    return render(request, 'crm/client_edit.html', {
        'client': client, 'form': form, 'vehicles': vehicles,
    })


@login_required
def vehicle_create(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    form = VehicleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        vehicle = form.save(commit=False)
        vehicle.client = client
        plate = ''.join(vehicle.plate_number.upper().split())
        if client.vehicles.filter(plate_number=plate).exists():
            form.add_error('plate_number', 'Автомобиль с таким госномером уже добавлен этому клиенту.')
        else:
            vehicle.plate_number = plate
            vehicle.save()
            messages.success(request, f'Автомобиль {vehicle.plate_number} добавлен клиенту.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': True, 'plate_number': vehicle.plate_number})
            return redirect('crm:client_detail', pk=client.pk)
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'errors': {name: [str(error) for error in errors] for name, errors in form.errors.items()}}, status=400)
    return render(request, 'crm/vehicle_form.html', {'client': client, 'form': form})


@login_required
@transaction.atomic
def service_edit(request, pk):
    service = get_object_or_404(
        ServiceRecord.objects.select_related('client', 'vehicle'), pk=pk
    )
    form = ServiceEditForm(request.POST or None, request.FILES or None, instance=service)
    if request.method == 'POST' and form.is_valid():
        new_files = request.FILES.getlist('service_files')
        if service.files.count() + len(new_files) > 3:
            form.add_error('service_files', 'У услуги может быть не более 3 файлов. Удалите старый файл или добавьте меньше новых.')
        else:
            form.save()
            for uploaded in new_files:
                ServiceFile.objects.create(service=service, file=uploaded)
            messages.success(request, 'Услуга успешно обновлена.')
            return redirect('crm:client_detail', pk=service.client_id)
    return render(request, 'crm/service_edit.html', {'service': service, 'form': form})


@login_required
def service_close(request, pk):
    service = get_object_or_404(
        ServiceRecord.objects.select_related('client', 'vehicle'), pk=pk
    )
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        if reason not in dict(ServiceRecord.CloseReason.choices):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': 'Выберите причину закрытия.'}, status=400)
            messages.error(request, 'Выберите причину закрытия услуги.')
        else:
            service.closed_at = timezone.now()
            service.closed_reason = reason
            service.closed_by = request.user
            service.save(update_fields=['closed_at', 'closed_reason', 'closed_by'])
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': True, 'status': service.status,
                    'status_label': service.status_label,
                    'reason_label': service.get_closed_reason_display(),
                })
            messages.success(
                request, 'Предупреждение закрыто. Услуга сохранена в истории клиента.'
            )
            if request.GET.get('next') == 'dashboard':
                return redirect('crm:dashboard')
            return redirect('crm:client_detail', pk=service.client_id)
    return render(request, 'crm/service_close.html', {
        'service': service, 'close_reasons': ServiceRecord.CloseReason.choices,
    })


@login_required
@transaction.atomic
def service_delete(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    service = get_object_or_404(
        ServiceRecord.objects.select_related('client', 'vehicle'), pk=pk
    )
    if not request.user.check_password(request.POST.get('password', '')):
        return JsonResponse({
            'ok': False, 'error': 'Неверный пароль. Услуга не удалена.'
        }, status=400)
    status = service.status
    service.delete()
    return JsonResponse({'ok': True, 'status': status})


@login_required
def client_file_delete(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied
    item = get_object_or_404(ClientFile, pk=pk)
    client_id = item.client_id
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Файл клиента удалён.')
    return redirect('crm:client_edit', pk=client_id)


@login_required
def service_file_delete(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied
    item = get_object_or_404(ServiceFile.objects.select_related('service'), pk=pk)
    service_id = item.service_id
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Файл услуги удалён.')
    return redirect('crm:service_edit', pk=service_id)


@login_required
def service_type_select(request):
    return render(request, 'crm/service_type_select.html', {
        'service_types': ServiceRecord.ServiceType.choices,
    })


@login_required
@transaction.atomic
def service_create(request, service_type):
    valid_types = dict(ServiceRecord.ServiceType.choices)
    if service_type not in valid_types:
        return redirect('crm:dashboard')
    initial = {'issued_on': timezone.localdate()}
    renewing_service = None
    renew_id = request.GET.get('renew')
    if renew_id:
        renewing_service = get_object_or_404(
            ServiceRecord.objects.select_related('client', 'vehicle'),
            pk=renew_id, service_type=service_type,
        )
        initial.update({
            'existing_client': renewing_service.client,
            'existing_vehicle': renewing_service.vehicle,
        })
    client_id = request.GET.get('client')
    if client_id and not renewing_service:
        initial['existing_client'] = Client.objects.filter(pk=client_id).first()
    form = ServiceCreateForm(request.POST or None, request.FILES or None, initial=initial)
    additional_types = [item for item in ServiceRecord.ServiceType.choices if item[0] != service_type]
    additional_initial = [{'service_type': value} for value, _label in additional_types]
    additional_services = AdditionalServiceFormSet(
        request.POST or None, request.FILES or None, prefix='additional', initial=additional_initial,
    )
    additional_posted = 'additional-TOTAL_FORMS' in request.POST
    additional_valid = bool(renewing_service) or not additional_posted or additional_services.is_valid()
    if request.method == 'POST' and form.is_valid() and additional_valid:
        issued_on = form.cleaned_data['issued_on']
        invalid_extra_expiry = False
        for extra_form in ([] if renewing_service or not additional_posted else additional_services):
            if not extra_form.cleaned_data.get('enabled'):
                continue
            expires_on = extra_form.cleaned_data.get('expires_on')
            if expires_on and expires_on < issued_on:
                extra_form.add_error('expires_on', 'Дата окончания не может быть раньше даты оформления.')
                invalid_extra_expiry = True
        if invalid_extra_expiry:
            return _render_service_create(
                request, form, additional_services, service_type, valid_types,
                vehicle_owners=None, renewing_service=renewing_service,
            )
        client = form.cleaned_data['existing_client']
        if not client:
            client = Client.objects.create(
                full_name=form.cleaned_data['full_name'], phone=form.cleaned_data['phone']
            )
        for uploaded in request.FILES.getlist('passport_files'):
            ClientFile.objects.create(client=client, file=uploaded)

        vehicle = form.cleaned_data['existing_vehicle']
        if not vehicle:
            vehicle, _ = Vehicle.objects.get_or_create(
                client=client,
                plate_number=''.join(form.cleaned_data['plate_number'].upper().split()),
            )
        services_to_create = [{
            'service_type': service_type,
            'expires_on': form.cleaned_data['expires_on'],
            'price': form.cleaned_data['price'],
            'notes': form.cleaned_data['notes'],
            'document_recipient': form.cleaned_data['document_recipient'],
            'files': request.FILES.getlist('service_files'),
        }]
        for index, extra_form in enumerate([] if renewing_service or not additional_posted else additional_services):
            if extra_form.cleaned_data.get('enabled'):
                services_to_create.append({
                    'service_type': extra_form.cleaned_data['service_type'],
                    'expires_on': extra_form.cleaned_data['expires_on'],
                    'price': extra_form.cleaned_data['price'],
                    'notes': '',
                    'document_recipient': form.cleaned_data['document_recipient'],
                    'files': request.FILES.getlist(f'additional-{index}-service_files'),
                })
        for service_data in services_to_create:
            attached_files = service_data.pop('files')
            service = ServiceRecord.objects.create(
                client=client, vehicle=vehicle, issued_on=issued_on,
                created_by=request.user, **service_data,
            )
            ServiceRecord.objects.select_for_update().filter(
                vehicle=vehicle, service_type=service.service_type, renewed_by__isnull=True,
                closed_at__isnull=True,
            ).exclude(pk=service.pk).update(renewed_by=service)
            for uploaded in attached_files:
                ServiceFile.objects.create(service=service, file=uploaded)
        messages.success(request, f'Создано услуг: {len(services_to_create)}. Клиент: {client.full_name}.')
        return redirect('crm:client_detail', pk=client.pk)
    return _render_service_create(
        request, form, additional_services, service_type, valid_types,
        vehicle_owners=None, renewing_service=renewing_service,
    )


def _render_service_create(
    request, form, additional_services, service_type, valid_types,
    vehicle_owners=None, renewing_service=None,
):
    vehicles = list(Vehicle.objects.select_related('client').only('pk', 'client_id', 'plate_number'))
    vehicle_owners = vehicle_owners or {str(vehicle.pk): vehicle.client_id for vehicle in vehicles}
    client_vehicles = {}
    for vehicle in vehicles:
        client_vehicles.setdefault(str(vehicle.client_id), []).append({
            'id': str(vehicle.pk), 'plate': vehicle.plate_number,
        })
    return render(request, 'crm/service_form.html', {
        'form': form, 'service_type': service_type, 'service_name': valid_types[service_type],
        'vehicle_owners': vehicle_owners, 'client_vehicles': client_vehicles,
        'additional_services': additional_services,
        'additional_type_labels': dict(ServiceRecord.ServiceType.choices),
        'renewing_service': renewing_service,
    })
