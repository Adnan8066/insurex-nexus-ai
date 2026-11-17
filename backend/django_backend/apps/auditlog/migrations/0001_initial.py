import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name='AuditEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entity_type', models.CharField(db_index=True, max_length=40)),
                ('entity_id', models.CharField(db_index=True, max_length=64)),
                ('entity_label', models.CharField(blank=True, max_length=120)),
                ('action', models.CharField(choices=[('created', 'Created'), ('updated', 'Updated')], max_length=12)),
                ('changes', models.JSONField(default=dict)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-timestamp', '-id']},
        ),
        migrations.AddIndex(
            model_name='auditevent',
            index=models.Index(fields=['entity_type', 'entity_id', '-timestamp'], name='auditlog_au_entity_8cb871_idx'),
        ),
    ]
