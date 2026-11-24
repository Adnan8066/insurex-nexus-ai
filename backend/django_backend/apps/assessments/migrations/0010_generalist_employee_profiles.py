from django.conf import settings
from django.db import migrations, models


def mark_unconfigured_profiles_as_generalists(apps, schema_editor):
    RoutingAgentProfile = apps.get_model('assessments', 'RoutingAgentProfile')
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(app_label, model_name)
    for user in User.objects.filter(role='employee', is_active=True).iterator():
        RoutingAgentProfile.objects.get_or_create(
            user_id=user.pk,
            defaults={'primary_specialization': 'all claims'},
        )
    RoutingAgentProfile.objects.filter(
        is_demo=False,
        primary_specialization='',
    ).update(primary_specialization='all claims')


class Migration(migrations.Migration):

    dependencies = [
        ('assessments', '0009_merge_20261117_1044'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='routingagentprofile',
            name='primary_specialization',
            field=models.CharField(
                blank=True,
                default='all claims',
                max_length=100,
                verbose_name='primary specialization',
            ),
        ),
        migrations.RunPython(
            mark_unconfigured_profiles_as_generalists,
            migrations.RunPython.noop,
        ),
    ]
