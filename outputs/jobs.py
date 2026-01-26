import logging

from django.utils import translation
from django.utils.module_loading import import_string
from pragmatic.utils import get_task_decorator

from outputs.usecases import export_items

try:
    # older Django
    from django.utils.translation import ugettext_lazy as _
except ImportError:
    # Django >= 3
    from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

task = get_task_decorator("exports")

@task
def mail_export_by_id(export_id, export_class_name, language, filename=None):
    try:
        from outputs.models import Export
        export_class = import_string(export_class_name)
        export = export_class.objects.get(id=export_id)

        export.status = Export.STATUS_PROCESSING
        export.save(update_fields=['status'])

        # set language
        translation.activate(language)

        # mail export
        export_items(export, language, filename)
    except Exception as e:
        logger.error(f"Failed to mail export by ID: export_id={export_id}, error={str(e)}", exc_info=True)
        raise
