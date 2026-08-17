from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0014_alter_appearancesetting_theme'),
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
                ('violet', 'Яркий фиолетовый'),
                ('coral', 'Яркий коралл'),
            ], default='indigo', max_length=16, verbose_name='Цветовая тема'),
        ),
    ]
