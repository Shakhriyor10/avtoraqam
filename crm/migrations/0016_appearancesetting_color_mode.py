from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0015_alter_appearancesetting_theme'),
    ]

    operations = [
        migrations.AddField(
            model_name='appearancesetting',
            name='color_mode',
            field=models.CharField(
                choices=[('light', 'Дневной режим'), ('dark', 'Тёмный режим')],
                default='light', max_length=8, verbose_name='Режим интерфейса',
            ),
        ),
    ]
