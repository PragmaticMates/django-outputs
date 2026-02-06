# Generated migration to update XML MRP format to XML

from django.db import migrations


def update_xml_mrp_to_xml(apps, schema_editor):
    """
    Update all Export and Scheduler records that have format='XML MRP' to format='XML'.
    """
    Export = apps.get_model('outputs', 'Export')
    Scheduler = apps.get_model('outputs', 'Scheduler')
    
    # Update Export records
    Export.objects.filter(format='XML_MRP').update(format='XML')
    
    # Update Scheduler records
    Scheduler.objects.filter(format='XML_MRP').update(format='XML')


def reverse_update_xml_mrp_to_xml(apps, schema_editor):
    """
    Reverse migration: change XML back to XML MRP.
    Note: This may not be accurate if there were originally both XML and XML MRP records.
    """
    Export = apps.get_model('outputs', 'Export')
    Scheduler = apps.get_model('outputs', 'Scheduler')
    
    # Reverse: change XML back to XML_MRP
    # Note: This assumes all XML records should be XML_MRP, which may not be accurate
    Export.objects.filter(format='XML').update(format='XML_MRP')
    Scheduler.objects.filter(format='XML').update(format='XML_MRP')


class Migration(migrations.Migration):

    dependencies = [
        ('outputs', '0022_remove_export_items'),
    ]

    operations = [
        migrations.RunPython(update_xml_mrp_to_xml, reverse_update_xml_mrp_to_xml),
    ]

