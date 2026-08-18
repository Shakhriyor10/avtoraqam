from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone


class Client(models.Model):
    full_name = models.CharField('ФИО', max_length=255)
    phone = models.CharField('Телефон', max_length=32, db_index=True)
    notes = models.TextField('Примечание', blank=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'клиент'
        verbose_name_plural = 'клиенты'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} — {self.phone}'


class ClientFile(models.Model):
    client = models.ForeignKey(Client, related_name='files', on_delete=models.CASCADE)
    file = models.FileField('Файл паспорта', upload_to='clients/passports/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class ClientFavorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='favorite_clients', on_delete=models.CASCADE
    )
    client = models.ForeignKey(Client, related_name='favorited_by', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'избранный клиент'
        verbose_name_plural = 'избранные клиенты'
        constraints = [
            models.UniqueConstraint(fields=['user', 'client'], name='unique_user_favorite_client')
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} · {self.client}'


class Vehicle(models.Model):
    client = models.ForeignKey(Client, related_name='vehicles', on_delete=models.CASCADE)
    plate_number = models.CharField('Госномер', max_length=24, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'автомобиль'
        verbose_name_plural = 'автомобили'
        constraints = [
            models.UniqueConstraint(fields=['client', 'plate_number'], name='unique_client_plate')
        ]

    def save(self, *args, **kwargs):
        self.plate_number = ''.join(self.plate_number.upper().split())
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.plate_number} · {self.client.full_name}'


class ServiceRecord(models.Model):
    class ServiceType(models.TextChoices):
        AVTORAQAM = 'avtoraqam', 'Avtoraqam'
        INSURANCE = 'insurance', 'Страховка'
        TINTING = 'tinting', 'Тонировка'
        POWER_OF_ATTORNEY = 'power_of_attorney', 'Доверенность'
        OTHER = 'other', 'Прочие услуги'

    class CloseReason(models.TextChoices):
        ELSEWHERE = 'elsewhere', 'Оформлено в другом месте'
        VEHICLE_SOLD = 'vehicle_sold', 'Машина была продана'
        DECLINED = 'declined', 'Клиент отказался'
        NOT_RELEVANT = 'not_relevant', 'Услуга больше не актуальна'
        OTHER = 'other', 'Другая причина'

    class DocumentRecipient(models.TextChoices):
        OWNER = 'owner', 'Владелец авто'
        RELATIVE = 'relative', 'Родственник'
        STRANGER = 'stranger', 'Незнакомый'

    client = models.ForeignKey(Client, related_name='services', on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, related_name='services', on_delete=models.CASCADE)
    service_type = models.CharField('Тип услуги', max_length=32, choices=ServiceType.choices)
    title = models.CharField('Название', max_length=160, blank=True)
    issued_on = models.DateField('Дата оформления', default=timezone.localdate)
    expires_on = models.DateField('Действует до', null=True, blank=True)
    price = models.DecimalField('Стоимость', max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField('Примечание', blank=True)
    document_recipient = models.CharField(
        'Кому переданы документы', max_length=16,
        choices=DocumentRecipient.choices, blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='created_services', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Сотрудник'
    )
    notified_at = models.DateTimeField('Последнее уведомление', null=True, blank=True)
    renewed_by = models.ForeignKey(
        'self', related_name='previous_versions', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Продлена записью'
    )
    closed_at = models.DateTimeField('Закрыта вручную', null=True, blank=True)
    closed_reason = models.CharField(
        'Причина закрытия', max_length=32, choices=CloseReason.choices, blank=True
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='closed_services', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Закрыл сотрудник'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'услуга'
        verbose_name_plural = 'услуги'
        ordering = ['expires_on']
        indexes = [
            models.Index(fields=['service_type', 'expires_on'], name='service_type_expiry_idx'),
            models.Index(fields=['closed_at', 'expires_on'], name='service_closed_expiry_idx'),
        ]

    @property
    def days_left(self):
        if self.expires_on is None:
            return None
        return (self.expires_on - timezone.localdate()).days

    @property
    def status(self):
        if self.renewed_by_id:
            return 'renewed'
        if self.closed_at:
            return 'closed'
        if self.expires_on is None:
            return 'no_expiry'
        if self.days_left < 0:
            return 'expired'
        warning_days = getattr(self, '_warning_days', None)
        if warning_days is None:
            warning_days = ServiceNotificationSetting.get_warning_days(self.service_type)
        if self.days_left <= warning_days:
            return 'warning'
        return 'active'

    @property
    def status_label(self):
        return {
            'expired': 'Истекла', 'warning': 'Скоро истекает',
            'active': 'Активна', 'no_expiry': 'Без срока',
            'renewed': 'Продлена', 'closed': 'Закрыта',
        }[self.status]

    def __str__(self):
        return f'{self.get_service_type_display()} — {self.client.full_name}'


class ServiceFile(models.Model):
    service = models.ForeignKey(ServiceRecord, related_name='files', on_delete=models.CASCADE)
    file = models.FileField('Документ', upload_to='services/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class ServiceNotificationSetting(models.Model):
    service_type = models.CharField(
        'Тип услуги', max_length=32, choices=ServiceRecord.ServiceType.choices, unique=True
    )
    warning_days = models.PositiveSmallIntegerField('Предупреждать за, дней', default=14)

    class Meta:
        verbose_name = 'настройка уведомления'
        verbose_name_plural = 'настройки уведомлений'
        ordering = ['service_type']

    @classmethod
    def get_warning_days(cls, service_type):
        value = cls.objects.filter(service_type=service_type).values_list('warning_days', flat=True).first()
        return value if value is not None else settings.EXPIRY_WARNING_DAYS

    @classmethod
    def warning_days_map(cls):
        configured = dict(cls.objects.values_list('service_type', 'warning_days'))
        return {
            service_type: configured.get(service_type, settings.EXPIRY_WARNING_DAYS)
            for service_type, _label in ServiceRecord.ServiceType.choices
        }

    def __str__(self):
        return f'{self.get_service_type_display()}: {self.warning_days} дней'


class AppearanceSetting(models.Model):
    class ColorMode(models.TextChoices):
        LIGHT = 'light', 'Дневной режим'
        DARK = 'dark', 'Тёмный режим'

    class Theme(models.TextChoices):
        TEAL = 'teal', 'Фирменная бирюза'
        INDIGO = 'indigo', 'Премиальный индиго'
        OCEAN = 'ocean', 'Глубокий океан'
        EMERALD = 'emerald', 'Тёмный изумруд'
        RUBY = 'ruby', 'Благородный рубин'
        SKY = 'sky', 'Светлое небо'
        SAND = 'sand', 'Тёплый песок'
        VIOLET = 'violet', 'Яркий фиолетовый'
        CORAL = 'coral', 'Яркий коралл'

    theme = models.CharField('Цветовая тема', max_length=16, choices=Theme.choices, default=Theme.INDIGO)
    color_mode = models.CharField(
        'Режим интерфейса', max_length=8, choices=ColorMode.choices, default=ColorMode.LIGHT
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'оформление CRM'
        verbose_name_plural = 'оформление CRM'

    @classmethod
    def get_theme(cls):
        return cls.objects.filter(pk=1).values_list('theme', flat=True).first() or cls.Theme.INDIGO

    @classmethod
    def get_color_mode(cls):
        return cls.objects.filter(pk=1).values_list('color_mode', flat=True).first() or cls.ColorMode.LIGHT

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_theme_display()


def delete_file_after_commit(field_file):
    if field_file and field_file.name:
        transaction.on_commit(lambda: field_file.delete(save=False))


@receiver(post_delete, sender=ClientFile)
def delete_client_file_from_storage(sender, instance, **kwargs):
    delete_file_after_commit(instance.file)


@receiver(post_delete, sender=ServiceFile)
def delete_service_file_from_storage(sender, instance, **kwargs):
    delete_file_after_commit(instance.file)
