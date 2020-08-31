from django.utils.timezone import now

from outputs import jobs

#  todo review
# def schedule_export(scheduler_id):
def schedule_export(scheduler):
    from outputs.models import Scheduler

    # # get scheduler by its identifier
    # scheduler = Scheduler.objects.get(pk=scheduler_id)
    scheduler.refresh_from_db()

    # delay export job in background
    jobs.execute_export.delay(scheduler.exporter_class, scheduler.exporter_params, language=scheduler.language)

    # update list of execution datetimes
    scheduler.executions.append(now())
    scheduler.save(update_fields=['executions'])
