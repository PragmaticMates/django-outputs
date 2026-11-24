import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outputs', '0023_update_xml_mrp_to_xml'),
    ]

    operations = [
        migrations.AddField(
            model_name='export',
            name='external_emails',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.EmailField(max_length=254), blank=True, default=list, size=None),
        ),
        migrations.AddField(
            model_name='scheduler',
            name='external_emails',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.EmailField(max_length=254), blank=True, default=list, size=None),
        ),
    ]
