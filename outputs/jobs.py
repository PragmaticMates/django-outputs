import logging

from django.utils import translation
from django.utils.module_loading import import_string
from pragmatic.utils import get_task_decorator

from outputs.usecases import export_items
from outputs.utils import deserialize_exporter_params

logger = logging.getLogger(__name__)

task = get_task_decorator("exports")


@task
def execute_export(exporter_class, exporter_params, language):
    # Reconstruct ORM objects from safe primitives (user_id -> user, etc.)
    exporter_params = deserialize_exporter_params(exporter_params)
    if isinstance(exporter_class, str):
        exporter_class = import_string(exporter_class)

    # init exporter
    exporter = exporter_class(**exporter_params)
    try:
        # save export to DB
        export = exporter.save_export()
        logger.info(f"Export created: export_id={export.id}, total_items={export.total}")

        # send mail with export to recipients
        export.send_mail(language, exporter_params.get('filename', None))
    except Exception as e:
        logger.error(f"Failed to execute export: exporter_class={exporter.__class__}, error={str(e)}", exc_info=True)
        raise

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
