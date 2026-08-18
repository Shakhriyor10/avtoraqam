from django.urls import path

from . import views

app_name = 'crm'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('services/search/', views.service_search, name='service_search'),
    path('settings/notifications/', views.notification_settings, name='notification_settings'),
    path('settings/color-mode/', views.color_mode_toggle, name='color_mode_toggle'),
    path('settings/users/new/', views.user_create, name='user_create'),
    path('settings/users/<int:pk>/toggle/', views.user_toggle_active, name='user_toggle_active'),
    path('clients/', views.client_list, name='client_list'),
    path('clients/search/', views.client_search, name='client_search'),
    path('clients/favorites/', views.favorite_clients, name='favorite_clients'),
    path('clients/<int:pk>/favorite/', views.client_favorite_toggle, name='client_favorite_toggle'),
    path('clients/<int:pk>/vehicles/', views.client_vehicles, name='client_vehicles'),
    path('clients/new/', views.client_create, name='client_create'),
    path('clients/<int:pk>/', views.client_detail, name='client_detail'),
    path('clients/<int:pk>/edit/', views.client_edit, name='client_edit'),
    path('clients/<int:pk>/delete/', views.client_delete, name='client_delete'),
    path('clients/<int:client_pk>/vehicles/new/', views.vehicle_create, name='vehicle_create'),
    path('client-files/<int:pk>/delete/', views.client_file_delete, name='client_file_delete'),
    path('services/new/', views.service_type_select, name='service_type_select'),
    path('services/check-duplicate/', views.service_duplicate_check, name='service_duplicate_check'),
    path('services/new/<str:service_type>/', views.service_create, name='service_create'),
    path('services/<int:pk>/edit/', views.service_edit, name='service_edit'),
    path('services/<int:pk>/close/', views.service_close, name='service_close'),
    path('services/<int:pk>/delete/', views.service_delete, name='service_delete'),
    path('service-files/<int:pk>/delete/', views.service_file_delete, name='service_file_delete'),
]
