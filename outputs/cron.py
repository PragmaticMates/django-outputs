from django.utils.module_loading import import_string
from django.utils.timezone import now

from outputs.jobs import execute_export
from outputs.utils import serialize_exporter_params
from pragmatic.utils import dispatch_task


def schedule_export(scheduler_id, scheduler_class_name):
    # get scheduler by its identifier
    scheduler_class = import_string(scheduler_class_name)
    scheduler = scheduler_class.objects.get(pk=scheduler_id)

    # serialize params and dispatch export job in background
    dispatch_task(
        execute_export,
        scheduler.exporter_class.get_path(),
        serialize_exporter_params(scheduler.exporter_params),
        language=scheduler.language,
    )

    # update list of execution datetimes
    scheduler.executions.append(now())
    scheduler.save(update_fields=['executions'])
