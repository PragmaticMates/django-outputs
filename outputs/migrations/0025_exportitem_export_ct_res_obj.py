"""
Covering index for "not yet exported" lookups.

Projects filter objects by `NOT EXISTS` over the items of exports matching a
format / exporter path. With only the `export_id` index Postgres fetches every
matching item from the heap; this index turns it into an index-only scan
(5-12 s -> 0.3 s on 24M items). Built concurrently so writes are not blocked.
"""
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('outputs', '0024_external_emails'),
    ]

    operations = [
        AddIndexConcurrently(
            model_name='exportitem',
            index=models.Index(fields=['export', 'content_type', 'result', 'object_id'], name='exportitem_export_ct_res_obj'),
        ),
    ]
