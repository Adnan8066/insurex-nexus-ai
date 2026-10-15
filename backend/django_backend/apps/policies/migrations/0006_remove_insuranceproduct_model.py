from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('policies', '0005_remove_icici_private_car_product')]

    operations = [
        migrations.DeleteModel(name='InsuranceProduct'),
    ]
