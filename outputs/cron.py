from django.utils.timezone import now
from pragmatic.utils import class_for_name

from outputs import jobs


#  todo review
def schedule_export(scheduler_id, scheduler_class_name):

    # # get scheduler by its identifier
    module_name, class_name = scheduler_class_name.rsplit('.', 1)
    scheduler_class = class_for_name(module_name, class_name)
    scheduler = scheduler_class.objects.get(pk=scheduler_id)

    # delay export job in background
    jobs.execute_export.delay(scheduler.exporter_class, scheduler.exporter_params, language=scheduler.language)

    # update list of execution datetimes
    scheduler.executions.append(now())
    scheduler.save(update_fields=['executions'])
