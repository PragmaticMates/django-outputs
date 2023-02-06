from django.db import migrations

from outputs.models import Export, Scheduler, AbstractExport


def set_exporter_path_export(*args, **kwargs):
    for export in Export.objects.only('id'):
        export.exporter_path = AbstractExport.get_exporter_path(
            model_class=export.model_class,
            context=export.context,
            format=export.format)
        export.save(update_fields=['exporter_path'])


def set_exporter_path_scheduler(*args, **kwargs):
    for scheduler in Scheduler.objects.only('id'):
        scheduler.exporter_path = AbstractExport.get_exporter_path(
            model_class=scheduler.model_class,
            context=scheduler.context,
            format=scheduler.format)
        scheduler.save(update_fields=['exporter_path'])


def unset_exporter_path_export(*args, **kwargs):
    Export.objects.update(exporter_path='')


def unset_exporter_path_scheduler(*args, **kwargs):
    Scheduler.objects.update(exporter_path='')


class Migration(migrations.Migration):

    dependencies = [
        ('outputs', '0009_auto_20230111_1353'),
    ]

    operations = [
        migrations.RunPython(set_exporter_path_export, unset_exporter_path_export),
        migrations.RunPython(set_exporter_path_scheduler, unset_exporter_path_scheduler),
    ]
