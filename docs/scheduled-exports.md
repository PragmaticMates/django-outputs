# Scheduled Exports

A `Scheduler` instance wraps any exporter and triggers it on a cron schedule.

## Creating a scheduler

Schedulers can be created:

- Via the Django admin
- Via the UI at `outputs:scheduler_create`
- Directly from an existing `Export` at `outputs:scheduler_create_from_export` (pre-fills content type, fields, format, context, exporter path, query string, and recipients from the source export)

## Routine choices

| Routine | Cron (UTC) | Description |
|---|---|---|
| `DAILY` | `0 7 * * *` | Every day at 08:00 local (07:00 UTC) |
| `WEEKLY` | `0 7 * * 1` | Every Monday at 08:00 local |
| `MONTHLY` | `0 7 1 * *` | First day of each month at 08:00 local |
| `CUSTOM` | user-supplied | Arbitrary cron expression validated via `croniter` |

## Lifecycle management

The scheduler job is managed automatically via Django signals:

- **Create** – `post_save` registers a new cron job in Redis and stores its ID on the `Scheduler` record.
- **Update** – `pre_save` detects changes to `is_active`, `routine`, or `cron_string` and re-registers the job after saving.
- **Deactivate** (`is_active = False`) – the cron job is cancelled and `job_id` is cleared.
- **Delete** – `pre_delete` cancels the cron job before the record is removed, leaving no orphaned Redis jobs.

## Execution

Each time the cron fires, `schedule_export()` in `cron.py`:

1. Fetches the `Scheduler` record by its PK.
2. Calls `execute_export(scheduler.exporter, language=scheduler.language)`, which saves a new `Export` record and enqueues the mail job exactly as a manual export would.
3. Appends the execution timestamp to `scheduler.executions`.

See [Processing](processing.md) for the full async pipeline.
