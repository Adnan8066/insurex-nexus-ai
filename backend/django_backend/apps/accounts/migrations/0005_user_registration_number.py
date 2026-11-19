from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_reset_demo_admin_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='registration_number',
            field=models.CharField(blank=True, max_length=20, verbose_name='vehicle registration number'),
        ),
    ]
