from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0013_appearancesetting'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appearancesetting',
            name='theme',
            field=models.CharField(choices=[
                ('teal', 'Фирменная бирюза'),
                ('indigo', 'Премиальный индиго'),
                ('ocean', 'Глубокий океан'),
                ('emerald', 'Тёмный изумруд'),
                ('ruby', 'Благородный рубин'),
                ('sky', 'Светлое небо'),
                ('sand', 'Тёплый песок'),
            ], default='indigo', max_length=16, verbose_name='Цветовая тема'),
        ),
    ]
