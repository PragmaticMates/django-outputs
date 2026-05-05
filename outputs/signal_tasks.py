from pragmatic.signals import apm_custom_context


@apm_custom_context('tasks')
def schedule_scheduler(scheduler):
    scheduler.schedule()
