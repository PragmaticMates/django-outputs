# Processing: Jobs, Usecases, Cron, Signal tasks

This page documents the four modules that form the async processing pipeline.

```
View / Scheduler
      │
      ▼
 execute_export()          ← usecases.py  (entry point)
      │  saves Export + ExportItem rows
      │  calls Export.send_mail()
      │
      ▼
 mail_export_by_id()       ← jobs.py  (RQ task on "exports" queue)
      │
      ▼
 export_items()            ← usecases.py  (generates file, updates status)
      │
      ├─ success → mail_successful_export()   ← usecases.py
      └─ failure → notify_about_failed_export() ← usecases.py
```

Scheduled exports follow the same pipeline but enter via `schedule_export()` in `cron.py` instead of a view.

---

## Jobs (`outputs/jobs.py`)

Contains the RQ task that drives async export processing.

### `mail_export_by_id(export_id, export_class_name, language, filename=None)`

An RQ task enqueued on the **`exports`** queue. Called by `Export.send_mail()` after the `Export` record has been persisted.

Steps:

1. Resolves the export class from `export_class_name` using `import_string`, then fetches the `Export` by `export_id`.
2. Sets `export.status = PROCESSING` and saves.
3. Activates the requested `language` for i18n.
4. Delegates to `export_items()` in `usecases.py` to generate the file and send email.

Any exception is logged with full traceback and re-raised so RQ marks the job as failed.

The task decorator is obtained via `pragmatic.utils.get_task_decorator("exports")`, which wraps the function as an RQ job bound to the `exports` queue.

---

## Usecases (`outputs/usecases.py`)

Plain functions containing the core business logic. They are called by jobs, views, and the cron runner; nothing in this module is queue-specific.

### `execute_export(exporter, language)`

Entry point for triggering a new export from a view or the cron runner.

1. Calls `exporter.save_export()` to persist the `Export` and `ExportItem` records.
2. Calls `export.send_mail(language, filename)` to enqueue `mail_export_by_id` on the `exports` queue.

Raises on any error (the caller is responsible for handling or re-raising).

### `export_items(export, language, filename=None)`

Core processing function called inside the RQ worker.

1. Sets `export.status = PROCESSING`.
2. Activates `language` for i18n.
3. Instantiates the exporter from `export.exporter` and sets `exporter.items = export.object_list` so the exporter operates on the exact same rows that were snapshotted at export creation time.
4. Runs `exporter.export()` inside a `transaction.atomic()` block:
    - **On success**: sets `export.status = FINISHED`, bulk-updates all `ExportItem` rows to `RESULT_SUCCESS`, then calls `mail_successful_export()`.
    - **On failure**: sets `export.status = FAILED`, bulk-updates all `ExportItem` rows to `RESULT_FAILURE` (storing the exception message as `detail`), then calls `notify_about_failed_export()` and re-raises.

The status update and `ExportItem` bulk-update share the same `transaction.atomic()` block, so a crash after the file is generated but before the DB commit leaves the export in a consistent `FAILED` state.

### `notify_about_failed_export(export, error_detail)`

Called when `export_items()` catches an exception.

- Logs the failure at `ERROR` level with full traceback.
- If `django-whistle` is installed, sends an `EXPORT_FAILED` in-app notification to the creator, all recipients, and all active superusers.

### `mail_successful_export(export, filename=None, output_file=None)`

Sends the completed export file to recipients.

- If `OUTPUTS_SAVE_AS_FILE = True`: saves the file to `exports/<filename>` via Django's `default_storage`, then passes the resulting URL to `get_message()` instead of attaching the file directly.
- If `export.send_separately = True`: sends one email per recipient address.
- Otherwise: sends a single email to all recipients at once.
- The file is **not attached** when `total == 0` (empty export) or when a `file_url` is available (storage mode).

### `get_message(exporter, count, recipient_list, subject, output_file=None, filename=None, file_url=None)`

Constructs an `EmailMultiAlternatives` message.

- Body is produced by `exporter.get_message_body(count, file_url)`.
- Subject is overridden by `exporter.get_message_subject()` if it returns a non-`None` value.
- The export file is attached (using `exporter.content_type` as MIME type) only when `count > 0` and no `file_url` is present.

---

## Cron (`outputs/cron.py`)

### `schedule_export(scheduler_id, scheduler_class_name)`

The function registered with `rq-scheduler` as a recurring cron job. It is stored in Redis by `Scheduler.schedule()` and invoked automatically on the configured schedule.

Steps:

1. Resolves `scheduler_class_name` via `import_string` and fetches the `Scheduler` by `scheduler_id`. Passing the class name (rather than a hard-coded import path) allows the `Scheduler` model to be subclassed in the host application.
2. Calls `execute_export(scheduler.exporter, language=scheduler.language)` to save a new `Export` record and enqueue the mail job.
3. Appends the current UTC datetime to `scheduler.executions` and saves only that field.

---

## Signal tasks (`outputs/signal_tasks.py`)

Small functions used as deferred tasks by signal handlers. They run outside the request/save transaction, either via `django-rq` or invoked directly after a signal fires.

### `notify_about_executed_export(export)`

Called 1 minute after a new `Export` is created (scheduled via `rq-scheduler` in the `export_executed_post_save` signal handler). Requires `django-whistle`.

Sends an `EXPORT_EXECUTED` in-app notification to all active superusers who are neither the creator nor a recipient of the export.

### `schedule_scheduler(scheduler)`

Called after a `Scheduler` is saved with changed scheduling fields (triggered by the `reschedule_scheduler` signal). Calls `scheduler.schedule()`, which cancels any existing cron job in Redis and registers a new one with the current settings.
