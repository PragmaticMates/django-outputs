from django.contrib.auth import get_user_model
from pragmatic.signals import apm_custom_context


@apm_custom_context('tasks')
def notify_about_executed_export(export):
    from whistle.helpers import notify
    notify_users = get_user_model().objects \
        .filter(is_active=True, is_superuser=True) \
        .exclude(pk=export.creator.pk) \
        .exclude(pk__in=export.recipients.all())

    for user in notify_users:
        notify(None, user, 'EXPORT_EXECUTED', actor=export.creator, object=export, target=export.content_type)


@apm_custom_context('tasks')
def schedule_scheduler(scheduler):
    scheduler.schedule()
