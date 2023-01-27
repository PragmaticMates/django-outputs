import json

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import migrations
from django.utils.module_loading import import_string

from outputs.models import AbstractExport


def reformat_export_fields_permissions(*args, **kwargs):
    if not hasattr(get_user_model(), 'export_fields_permissions'):
        return

    for user in get_user_model().objects.exclude(export_fields_permissions={}):
        permissions = user.export_fields_permissions
        new_permissions = {}

        if isinstance(permissions, str):
            permissions = json.loads(permissions)

        for key, fields in permissions.items():
            app_label, model_name, format = key.split('.')
            model_class = apps.get_model(app_label=app_label, model_name=model_name)
            exporter_path = AbstractExport.get_exporter_path(model_class, AbstractExport.CONTEXT_LIST, format)
            exporter = import_string(exporter_path)
            new_permissions[exporter.get_path()] = fields

        user.export_fields_permissions = new_permissions
        user.save(update_fields=['export_fields_permissions'])


def undo_reformat_export_fields_permissions(*args, **kwargs):
    if not hasattr(get_user_model(), 'export_fields_permissions'):
        return

    for user in get_user_model().objects.exclude(export_fields_permissions={}):
        permissions = user.export_fields_permissions
        old_permissions = {}

        if isinstance(permissions, str):
            permissions = json.loads(permissions)

        for key, fields in permissions.items():
            exporter = import_string(key)
            app_label, model_name = exporter.get_app_and_model()
            export_format = exporter.export_format
            export_format = export_format.capitalize()
            old_permission = '.'.join([app_label, model_name, export_format])
            old_permissions[old_permission] = fields

        user.export_fields_permissions = old_permissions
        user.save(update_fields=['export_fields_permissions'])


class Migration(migrations.Migration):
    dependencies = [
        ('outputs', '0010_set_exporter_path'),
    ]

    operations = [
        migrations.RunPython(reformat_export_fields_permissions, undo_reformat_export_fields_permissions),
    ]
