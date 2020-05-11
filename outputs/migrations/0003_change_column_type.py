from django.db import connection, migrations

from swida.migration_helpers import RunPython


def change_column_type(*args, **kwargs):
    with connection.cursor() as cursor:
        # changing type from character varying(16) to integer
        cursor.execute("ALTER TABLE public.outputs_export_items ALTER COLUMN gm2m_pk TYPE integer USING gm2m_pk::integer;")


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('outputs', '0002_import_billing_exports'),
    ]

    operations = [
        RunPython(change_column_type)
    ]
