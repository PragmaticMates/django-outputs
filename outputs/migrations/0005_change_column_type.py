from django.db import connection, migrations


def change_column_type(*args, **kwargs):
    with connection.cursor() as cursor:
        # changing type from character varying(16) to integer
        cursor.execute("ALTER TABLE public.outputs_export_items ALTER COLUMN gm2m_pk TYPE integer USING gm2m_pk::integer;")


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('outputs', '0004_auto_20200824_1418'),
    ]

    operations = [
        migrations.RunPython(change_column_type)
    ]
