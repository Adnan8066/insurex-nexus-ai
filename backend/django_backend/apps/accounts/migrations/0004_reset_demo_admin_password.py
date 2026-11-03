"""One-time reset of the hosted demo admin's forgotten password.

The free host has no shell, so this runs with the deploy's ``migrate``. Only the
hash is stored here, and migrations run once, so later password changes are kept.
"""

from django.db import migrations

ADMIN_EMAIL = 'admin@insurex.ai'
# make_password('demo1234')
PASSWORD_HASH = 'pbkdf2_sha256$1000000$BPGgidNuiXyQe5fWyCmnMe$wXcZy9/a46vCHDuhkOKxo8A9WvKR1DEqaKTAOS+/kto='


def reset_admin_password(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(email__iexact=ADMIN_EMAIL).update(password=PASSWORD_HASH, is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_user_manager'),
    ]

    operations = [
        migrations.RunPython(reset_admin_password, migrations.RunPython.noop),
    ]
