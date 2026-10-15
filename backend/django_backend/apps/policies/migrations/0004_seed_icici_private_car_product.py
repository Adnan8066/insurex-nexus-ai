from datetime import date

from django.db import migrations


def add_icici_private_car_product(apps, schema_editor):
    InsuranceProduct = apps.get_model('policies', 'InsuranceProduct')
    InsuranceProduct.objects.using(schema_editor.connection.alias).update_or_create(
        uin='IRDAN115RP0017V01200102',
        defaults={
            'insurer': 'ICICI Lombard General Insurance Company Limited',
            'product_name': 'Private Car Package Policy',
            'product_code': '3001',
            'vehicle_class': 'Private car',
            'cover_type': 'Package',
            'summary': (
                'Package motor insurance covering loss or damage to the insured car '
                'and third-party liability, subject to the policy wording and the '
                'cover selected in the policy schedule.'
            ),
            'product_url': 'https://www.icicilombard.com/motor-insurance/car-insurance',
            'wording_url': (
                'https://www.icicilombard.com/docs/default-source/default-document-library/'
                'private-car-package-policy-wording.pdf'
            ),
            'last_verified': date(2026, 10, 15),
            'is_available': True,
        },
    )


def remove_icici_private_car_product(apps, schema_editor):
    InsuranceProduct = apps.get_model('policies', 'InsuranceProduct')
    InsuranceProduct.objects.using(schema_editor.connection.alias).filter(
        uin='IRDAN115RP0017V01200102'
    ).delete()


class Migration(migrations.Migration):
    dependencies = [('policies', '0003_insuranceproduct')]

    operations = [
        migrations.RunPython(add_icici_private_car_product, remove_icici_private_car_product),
    ]
