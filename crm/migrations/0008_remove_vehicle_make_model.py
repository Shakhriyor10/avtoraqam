from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('crm', '0007_servicerecord_service_type_expiry_idx_and_more')]

    operations = [migrations.RemoveField(model_name='vehicle', name='make_model')]
