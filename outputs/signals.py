from datetime import timedelta

import django_rq
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from whistle.helpers import notify

from django.contrib.auth import get_user_model
from outputs.models import Export, Scheduler
from outputs.signal_tasks import notify_about_executed_export, schedule_scheduler
from pragmatic.signals import SignalsHelper, apm_custom_context


@receiver(post_save, sender=Export)
@apm_custom_context('signals')
def export_executed_post_save(sender, instance, created, **kwargs):
    if created:
        scheduler = django_rq.get_scheduler('default')

        # schedule export notifications
        scheduler.enqueue_in(
            time_delta=timedelta(minutes=1),
            func=notify_about_executed_export,
            export=instance,
        )


@receiver(pre_save, sender=Scheduler)
@apm_custom_context('signals')
def reschedule_scheduler(sender, instance, **kwargs):
    """
    Signal to check if routine of the scheduler changed.
    """
    if SignalsHelper.attribute_changed(instance, ['is_active', 'routine']):
        SignalsHelper.add_task_and_connect(sender, instance, schedule_scheduler, [instance])


@receiver(pre_delete, sender=Scheduler)
@apm_custom_context('signals')
def cancel_scheduler(sender, instance, **kwargs):
    """
    Delete redis queue job when scheduler is deleted
    """
    instance.cancel_schedule()


@receiver(post_save, sender=Scheduler)
@apm_custom_context('signals')
def notify_about_scheduler(sender, instance, created, **kwargs):
    """
    Signal to notify when scheduler is created.
    """
    if created:
        recipients = get_user_model().objects.managers().exclude(pk=instance.creator.pk)

        for recipient in recipients:
            notify(None, recipient, 'SCHEDULER_CREATED', actor=instance.creator, object=instance)
