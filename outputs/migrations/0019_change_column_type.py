from django.db import connection, migrations


def change_column_type(*args, **kwargs):
    with connection.cursor() as cursor:
        # changing type from character varying(16) to integer
        cursor.execute("ALTER TABLE public.outputs_export_items ALTER COLUMN gm2m_pk TYPE VARCHAR(10) USING gm2m_pk::VARCHAR(10);")


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('outputs', '0018_alter_export_url'),
    ]

    operations = [
        migrations.RunPython(change_column_type)
    ]
