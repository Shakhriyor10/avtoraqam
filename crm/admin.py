from django.contrib import admin

from .models import Client, ClientFile, ServiceFile, ServiceNotificationSetting, ServiceRecord, Vehicle


class ClientFileInline(admin.TabularInline):
    model = ClientFile
    extra = 0


class VehicleInline(admin.TabularInline):
    model = Vehicle
    extra = 0


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'created_at')
    search_fields = ('full_name', 'phone', 'vehicles__plate_number')
    inlines = [ClientFileInline, VehicleInline]


class ServiceFileInline(admin.TabularInline):
    model = ServiceFile
    extra = 0


@admin.register(ServiceRecord)
class ServiceRecordAdmin(admin.ModelAdmin):
    list_display = ('client', 'service_type', 'vehicle', 'expires_on', 'status_label')
    list_filter = ('service_type', 'expires_on')
    search_fields = ('client__full_name', 'client__phone', 'vehicle__plate_number')
    autocomplete_fields = ('client', 'vehicle')
    inlines = [ServiceFileInline]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('plate_number', 'client')
    search_fields = ('plate_number', 'client__full_name', 'client__phone')


@admin.register(ServiceNotificationSetting)
class ServiceNotificationSettingAdmin(admin.ModelAdmin):
    list_display = ('service_type', 'warning_days')
