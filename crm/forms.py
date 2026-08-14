from django import forms
from django.forms import BaseFormSet, BaseInlineFormSet, formset_factory, inlineformset_factory

from .models import Client, ServiceRecord, Vehicle


class MoneyField(forms.DecimalField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', forms.TextInput(attrs={
            'class': 'money-input', 'inputmode': 'decimal', 'autocomplete': 'off',
            'placeholder': 'Например: 1 000 000',
        }))
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if isinstance(value, str):
            value = value.replace(' ', '').replace('\u00a0', '').replace(',', '.')
        return super().to_python(value)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        self.max_files = kwargs.pop('max_files', 3)
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        clean_one = super().clean
        if isinstance(data, (list, tuple)):
            if len(data) > self.max_files:
                raise forms.ValidationError(f'Можно прикрепить не более {self.max_files} файлов.')
            return [clean_one(item, initial) for item in data]
        return clean_one(data, initial)


class ServiceCreateForm(forms.Form):
    existing_client = forms.ModelChoiceField(
        label='Существующий клиент', queryset=Client.objects.all(), required=False,
        empty_label='Создать нового клиента'
    )
    full_name = forms.CharField(label='ФИО нового клиента', max_length=255, required=False)
    phone = forms.CharField(label='Номер телефона', max_length=32, required=False)
    passport_files = MultipleFileField(
        label='Паспорт клиента — до 3 файлов', required=False, max_files=3
    )
    existing_vehicle = forms.ModelChoiceField(
        label='Существующий автомобиль', queryset=Vehicle.objects.select_related('client'),
        required=False, empty_label='Добавить новый автомобиль'
    )
    plate_number = forms.CharField(label='Госномер автомобиля', max_length=24, required=False)
    issued_on = forms.DateField(
        label='Дата оформления',
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
    )
    expires_on = forms.DateField(
        label='Действует до',
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
    )
    price = MoneyField(label='Стоимость, сум', max_digits=12, decimal_places=2, required=False)
    notes = forms.CharField(label='Примечание', required=False, widget=forms.Textarea(attrs={'rows': 3}))
    service_files = MultipleFileField(
        label='Документы услуги — до 3 файлов', required=False, max_files=3
    )
    document_recipient = forms.ChoiceField(
        label='Кому переданы документы', choices=[('', 'Не указано'), *ServiceRecord.DocumentRecipient.choices],
        required=False,
    )

    def clean(self):
        data = super().clean()
        client = data.get('existing_client')
        vehicle = data.get('existing_vehicle')
        if vehicle and not client:
            client = vehicle.client
            data['existing_client'] = client
        if not client and (not data.get('full_name') or not data.get('phone')):
            self.add_error('full_name', 'Выберите клиента или заполните ФИО и телефон.')
        if vehicle and client and vehicle.client_id != client.id:
            self.add_error('existing_vehicle', 'Автомобиль принадлежит другому клиенту.')
        passport_files = data.get('passport_files') or []
        if client and client.files.count() + len(passport_files) > 3:
            self.add_error(
                'passport_files',
                'У клиента может быть не более 3 файлов. Удалите старый файл или добавьте меньше новых.',
            )
        if not vehicle and not data.get('plate_number'):
            self.add_error('plate_number', 'Выберите автомобиль или укажите госномер.')
        issued = data.get('issued_on')
        expires = data.get('expires_on')
        if issued and expires and expires < issued:
            self.add_error('expires_on', 'Дата окончания не может быть раньше даты оформления.')
        return data


class ClientForm(forms.ModelForm):
    passport_files = MultipleFileField(
        label='Добавить файлы клиента', required=False, max_files=3
    )

    class Meta:
        model = Client
        fields = ['full_name', 'phone', 'notes']


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['plate_number']

    def clean_plate_number(self):
        return ''.join(self.cleaned_data['plate_number'].upper().split())


class VehicleInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        for form in self.forms:
            if (
                form.cleaned_data.get('DELETE') and form.instance.pk and
                form.instance.services.exists()
            ):
                raise forms.ValidationError(
                    'Нельзя удалить автомобиль, у которого есть история услуг.'
                )


VehicleFormSet = inlineformset_factory(
    Client, Vehicle, form=VehicleForm, formset=VehicleInlineFormSet,
    extra=1, can_delete=True
)


class AdditionalServiceForm(forms.Form):
    service_type = forms.ChoiceField(choices=ServiceRecord.ServiceType.choices, widget=forms.HiddenInput)
    enabled = forms.BooleanField(label='Добавить эту услугу', required=False)
    expires_on = forms.DateField(
        label='Действует до', required=False, input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
    )
    price = MoneyField(label='Стоимость, сум', max_digits=12, decimal_places=2, required=False)
    service_files = MultipleFileField(
        label='Документы услуги — до 3 файлов', required=False, max_files=3
    )
    def clean(self):
        data = super().clean()
        if data.get('enabled') and not data.get('expires_on'):
            self.add_error('expires_on', 'Укажите срок действия услуги.')
        return data


class AdditionalServiceBaseFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        selected = [
            form.cleaned_data.get('service_type') for form in self.forms
            if form.cleaned_data and form.cleaned_data.get('enabled')
        ]
        if len(selected) != len(set(selected)):
            raise forms.ValidationError('Одна и та же услуга выбрана несколько раз.')


AdditionalServiceFormSet = formset_factory(
    AdditionalServiceForm, formset=AdditionalServiceBaseFormSet, extra=0
)


class ServiceEditForm(forms.ModelForm):
    price = MoneyField(label='Стоимость, сум', max_digits=12, decimal_places=2, required=False)
    service_files = MultipleFileField(
        label='Добавить документы услуги', required=False, max_files=3
    )

    class Meta:
        model = ServiceRecord
        fields = ['vehicle', 'issued_on', 'expires_on', 'price', 'notes', 'document_recipient']
        widgets = {
            'issued_on': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'expires_on': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.client_id:
            self.fields['vehicle'].queryset = self.instance.client.vehicles.all()

    def clean(self):
        data = super().clean()
        issued = data.get('issued_on')
        expires = data.get('expires_on')
        if issued and expires and expires < issued:
            self.add_error('expires_on', 'Дата окончания не может быть раньше даты оформления.')
        return data
