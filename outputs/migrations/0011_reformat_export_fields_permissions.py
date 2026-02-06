from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('outputs', '0010_set_exporter_path'),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
