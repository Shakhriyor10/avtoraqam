from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('crm', '0008_remove_vehicle_make_model')]

    operations = [
        migrations.AddField(
            model_name='servicerecord',
            name='document_recipient',
            field=models.CharField(
                blank=True,
                choices=[
                    ('ota', 'ОТА'), ('ona', 'ОНА'), ('er', 'ЭР'), ('xotin', 'ХОТИН'),
                    ('ugil', 'УГИЛ'), ('qiz', 'КИЗ'), ('aka', 'АКА'), ('uka', 'УКА'),
                    ('opa', 'ОПА'), ('singil', 'СИНГИЛ'),
                ],
                max_length=16,
                verbose_name='Кому переданы документы',
            ),
        ),
    ]
