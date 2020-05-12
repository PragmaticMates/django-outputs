from django.utils.timezone import now

from outputs import jobs


def schedule_export(scheduler_id):
    from outputs.models import Scheduler

    # get scheduler by its identifier
    scheduler = Scheduler.objects.get(pk=scheduler_id)

    # delay export job in background
    jobs.execute_export.delay(scheduler.exporter_class, scheduler.exporter_params, language=scheduler.language)

    # update list of execution datetimes
    scheduler.executions.append(now())
    scheduler.save(update_fields=['executions'])
