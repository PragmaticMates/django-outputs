# Models

All models live in `outputs.models`.

## `AbstractExport`

Abstract base class shared by `Export` and `Scheduler`. Holds the fields that describe *what* should be exported:

| Field | Type | Description |
|---|---|---|
| `content_type` | FK → `ContentType` | The Django model being exported |
| `format` | `CharField` | `XLSX`, `XML`, or `PDF` |
| `context` | `CharField` | `LIST`, `STATISTICS`, or `DETAIL` |
| `exporter_path` | `CharField` | Dotted import path of the exporter class |
| `fields` | `ArrayField` | List of selected field attribute names; `None` means all fields |
| `query_string` | `TextField` | URL-encoded filter parameters |
| `creator` | FK → `AUTH_USER_MODEL` | User who created the export |
| `recipients` | M2M → `User` | Users who will receive the export email |
| `send_separately` | `BooleanField` | Send one email per recipient instead of a single combined email |
| `created` / `modified` | `DateTimeField` | Auto-managed timestamps |

Notable properties:

- **`model_class`** – Returns the Python model class from `content_type`.
- **`exporter_class`** – Imports and returns the exporter class from `exporter_path`.
- **`exporter`** – Instantiates the exporter, automatically dropping constructor arguments the class does not accept.
- **`params`** – Returns `query_string` as a `QueryDict`.
- **`get_params_display()`** – Returns a human-readable multiline string of active filter values, falling back to raw key/value pairs if the exporter cannot be imported.
- **`get_fields_labels()`** – Returns display labels for the selected fields by consulting `selectable_fields()` on the exporter.

---

## `Export`

Tracks a single export request through its lifecycle.

Additional fields beyond `AbstractExport`:

| Field | Type | Description |
|---|---|---|
| `status` | `CharField` | `PENDING` → `PROCESSING` → `FINISHED` / `FAILED` |
| `output_type` | `CharField` | `FILE` (attach to email) or `STREAM` (direct download) |
| `total` | `PositiveIntegerField` | Number of items in the export |
| `emails` | `ArrayField` | Snapshot of recipient email addresses at export time |
| `url` | `URLField` | URL of the originating list view |

Notable properties and methods:

- **`object_list`** – Returns a queryset of the actual model instances tracked by the associated `ExportItem` records. Provides the same API as the former GM2M `items` field.
- **`update_export_items_result(result, detail='')`** – Bulk-updates all `ExportItem` rows for this export with a success or failure result.
- **`send_mail(language, filename=None)`** – Enqueues the `mail_export_by_id` RQ job on the `exports` queue.
- **`get_absolute_url()`** – Returns the originating list URL with the original query string appended.
- **`get_items_url()`** – Returns the list URL filtered to only the items in this export (`?export=<pk>`).

Manager: `ExportQuerySet` (currently a plain queryset; use Django ORM filters directly).

If `django-auditlog` is installed, changes to `Export` are recorded automatically (excluding `modified` and `creator`).

---

## `ExportItem`

Stores one row per object included in an export. Replaced the former GM2M generic relation.

| Field | Type | Description |
|---|---|---|
| `export` | FK → `Export` | Parent export (cascade delete, `related_name='items'`) |
| `content_type` | FK → `ContentType` | Model type of the exported object |
| `object_id` | `PositiveIntegerField` | PK of the exported object |
| `result` | `CharField` | `SUCCESS`, `FAILURE`, or empty (not yet processed) |
| `detail` | `TextField` | String representation of the object, or error message on failure |
| `created` / `modified` | `DateTimeField` | Auto-managed timestamps |

Indexes are defined on `(content_type, object_id)`, `(export, result)`, and `(export, created)` for efficient querying.

Custom queryset methods on `ExportItemQuerySet`:

- **`.successful()`** – Filter to `result=SUCCESS`.
- **`.failed()`** – Filter to `result=FAILURE`.
- **`.for_object(object_id, content_type)`** – Filter to a specific object.
- **`.by_export_id(export_id)`** – Filter by parent export PK.

---

## `Scheduler`

Extends `AbstractExport` with cron scheduling metadata.

Additional fields:

| Field | Type | Description |
|---|---|---|
| `routine` | `CharField` | `DAILY`, `WEEKLY`, `MONTHLY`, or `CUSTOM` |
| `cron_string` | `CharField` | User-supplied cron expression (only when `routine=CUSTOM`) |
| `is_active` | `BooleanField` | Whether the scheduler is currently running |
| `executions` | `ArrayField` | List of datetime stamps each time the scheduler has run |
| `job_id` | `CharField` | UUID of the `rq-scheduler` cron job |
| `language` | `CharField` | Language code used when rendering the exported file and email |

A database `CheckConstraint` enforces that `cron_string` is non-empty if and only if `routine=CUSTOM`.

Notable methods:

- **`schedule()`** – Cancels any existing cron job, then (re-)registers the scheduler with `rq-scheduler` if `is_active=True`. Saves the new `job_id`.
- **`cancel_schedule()`** – Deletes the RQ job without touching the database record.
- **`get_cron_string()`** – Returns the effective cron expression for the chosen routine (all times are UTC: daily/weekly/monthly fire at 07:00 UTC).
- **`cron_description`** (property) – Returns a localised human-readable description via `cron-descriptor`.
- **`is_scheduled`** (property) – `True` if an active RQ job exists for this scheduler.
- **`schedule_time`** (property) – Next scheduled execution time, converted to the project's `TIME_ZONE`.

Custom queryset method on `SchedulerQuerySet`:

- **`.active()`** – Filter to `is_active=True`.

If `django-auditlog` is installed, changes are recorded (excluding `modified`, `creator`, `executions`, and `job_id`).
