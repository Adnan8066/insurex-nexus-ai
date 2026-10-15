from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('assessments', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='claimassessment',
            name='comparable_claims_count',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name='comparable claims count',
            ),
        ),
    ]
