from django.utils.module_loading import import_string
from django.utils.timezone import now

from outputs import jobs


# TODO: review
def schedule_export(scheduler_id, scheduler_class_name):
    # get scheduler by its identifier
    scheduler_class = import_string(scheduler_class_name)
    scheduler = scheduler_class.objects.get(pk=scheduler_id)

    # delay export job in background
    jobs.execute_export.delay(scheduler.exporter_class, scheduler.exporter_params, language=scheduler.language)

    # update list of execution datetimes
    scheduler.executions.append(now())
    scheduler.save(update_fields=['executions'])
