from django.db import migrations

from outputs.models import Scheduler


def reschedule_schedulers(*args, **kwargs):
    for scheduler in Scheduler.objects.all():
        scheduler.schedule()


class Migration(migrations.Migration):

    dependencies = [
        ('outputs', '0013_auto_20230125_1259'),
    ]

    operations = [
        migrations.RunPython(reschedule_schedulers, migrations.RunPython.noop)
    ]