import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assessments', '0005_routingagentprofile_is_demo'),
    ]

    operations = [
        migrations.AddField(
            model_name='routingagentprofile', name='designation',
            field=models.CharField(blank=True, max_length=120, verbose_name='designation'),
        ),
        migrations.AddField(
            model_name='routingagentprofile', name='years_of_experience',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='years of experience'),
        ),
        migrations.AddField(
            model_name='routingagentprofile', name='max_claim_capacity',
            field=models.PositiveSmallIntegerField(default=10, verbose_name='maximum active claims'),
        ),
        migrations.AddField(
            model_name='routingagentprofile', name='availability_status',
            field=models.CharField(
                choices=[('available', 'Available'), ('busy', 'Busy'), ('on_leave', 'On Leave'),
                         ('off_duty', 'Off Duty'), ('temporarily_unavailable', 'Temporarily Unavailable')],
                default='available', max_length=32, verbose_name='availability status',
            ),
        ),
        migrations.AddField(
            model_name='routingagentprofile', name='working_days',
            field=models.JSONField(blank=True, default=list, verbose_name='working days'),
        ),
        migrations.AddField(
            model_name='routingagentprofile', name='shift_start_time',
            field=models.TimeField(blank=True, null=True, verbose_name='shift start time'),
        ),
        migrations.AddField(
            model_name='routingagentprofile', name='shift_end_time',
            field=models.TimeField(blank=True, null=True, verbose_name='shift end time'),
        ),
        migrations.AddField(
            model_name='routingagentprofile', name='leave_status',
            field=models.CharField(blank=True, max_length=120, verbose_name='leave status'),
        ),
        migrations.CreateModel(
            name='EmployeeSkill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='skill or specialization')),
                ('level', models.CharField(choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'),
                                                    ('advanced', 'Advanced'), ('expert', 'Expert')],
                                           max_length=20, verbose_name='expertise level')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name='skills', to='assessments.routingagentprofile')),
            ],
            options={'db_table': 'employee_skills', 'ordering': ['name']},
        ),
        migrations.AddConstraint(
            model_name='employeeskill',
            constraint=models.UniqueConstraint(fields=('profile', 'name'), name='unique_employee_profile_skill'),
        ),
    ]
