# Signals

Signals are defined in `outputs.signals` and connected automatically when the app loads.

## `export_executed_post_save` (`post_save` on `Export`)

Fires when a new `Export` record is created. If `django-whistle` is installed, schedules a delayed RQ task (1 minute) via `notify_about_executed_export` that notifies all active superusers (excluding the creator and recipients) with an `EXPORT_EXECUTED` event.

## `reschedule_scheduler` (`pre_save` on `Scheduler`)

Fires before a `Scheduler` is saved. If `is_active`, `routine`, or `cron_string` has changed, enqueues `schedule_scheduler` (which calls `scheduler.schedule()`) to run after the save completes. This keeps the RQ cron job in sync with any change to the scheduler's settings.

## `cancel_scheduler` (`pre_delete` on `Scheduler`)

Fires before a `Scheduler` is deleted. Calls `scheduler.cancel_schedule()` to remove the corresponding RQ cron job so no orphaned jobs remain in Redis.

## `notify_about_scheduler` (`post_save` on `Scheduler`)

Fires when a new `Scheduler` is created. If `django-whistle` is installed, sends a `SCHEDULER_CREATED` notification to all manager-level users (excluding the creator).

## `update_export_item` (custom `export_item_changed` signal)

A custom `Signal` instance exported as `outputs.signals.export_item_changed`. Send it to create or update an `ExportItem` for a specific `(export_id, content_type, object_id)` combination:

```python
from outputs.signals import export_item_changed
from django.contrib.contenttypes.models import ContentType
from outputs.models import ExportItem

export_item_changed.send(
    sender=MyModel,
    export_id=export.pk,
    content_type=ContentType.objects.get_for_model(MyModel),
    object_id=instance.pk,
    result=ExportItem.RESULT_SUCCESS,
    detail=str(instance),
)
```
