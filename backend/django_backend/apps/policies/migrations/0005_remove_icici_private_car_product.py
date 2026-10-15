from django.db import migrations


def remove_icici_private_car_product(apps, schema_editor):
    InsuranceProduct = apps.get_model('policies', 'InsuranceProduct')
    InsuranceProduct.objects.using(schema_editor.connection.alias).filter(
        uin='IRDAN115RP0017V01200102'
    ).delete()


class Migration(migrations.Migration):
    dependencies = [('policies', '0004_seed_icici_private_car_product')]

    operations = [
        migrations.RunPython(remove_icici_private_car_product, migrations.RunPython.noop),
    ]
