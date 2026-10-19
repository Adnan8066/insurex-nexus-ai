from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CallbackRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='name')),
                ('phone', models.CharField(max_length=20, verbose_name='contact number')),
                ('vehicle_type', models.CharField(choices=[('car', 'Car'), ('two_wheeler', 'Two-wheeler'), ('commercial', 'Commercial vehicle'), ('other', 'Other')], max_length=20, verbose_name='vehicle type')),
                ('consent', models.BooleanField(verbose_name='consent to be contacted')),
                ('status', models.CharField(choices=[('new', 'New'), ('contacted', 'Contacted'), ('closed', 'Closed')], default='new', max_length=20, verbose_name='status')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='requested at')),
            ],
            options={
                'verbose_name': 'callback request',
                'verbose_name_plural': 'callback requests',
                'db_table': 'callback_requests',
                'ordering': ['-created_at'],
            },
        ),
    ]
