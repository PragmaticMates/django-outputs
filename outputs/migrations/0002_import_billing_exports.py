from django.contrib.contenttypes.models import ContentType
from django.db import migrations
from freezegun import freeze_time

from invoicing.models import Invoice
from outputs.models import Export
from swida.migration_helpers import RunPython


def import_billing_exports(*args, **kwargs):
    try:
        from swida.core.billing.models import Export as BillingExport

        for billing_export in BillingExport.objects.all().defer('context'):
            with freeze_time(billing_export.created):
                export = Export.objects.create(
                    content_type=ContentType.objects.get_for_model(Invoice),
                    format=billing_export.output,
                    creator=billing_export.creator,
                    total=billing_export.total
                )
                export.recipients.add(billing_export.creator)
                export.items.add(*list(billing_export.invoices.all()))
    except ImportError:
        print('import_billing_exports: swida.core.billing.models.Export could not be imported')
        pass


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('outputs', '0001_initial'),
    ]

    operations = [
        RunPython(import_billing_exports, lambda: Export.objects.delete())
    ]
