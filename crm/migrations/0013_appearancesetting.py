from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0012_alter_servicerecord_document_recipient'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppearanceSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('theme', models.CharField(choices=[
                    ('teal', 'Фирменная бирюза'),
                    ('indigo', 'Премиальный индиго'),
                    ('ocean', 'Глубокий океан'),
                    ('emerald', 'Тёмный изумруд'),
                    ('ruby', 'Благородный рубин'),
                ], default='indigo', max_length=16, verbose_name='Цветовая тема')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'оформление CRM',
                'verbose_name_plural': 'оформление CRM',
            },
        ),
    ]
