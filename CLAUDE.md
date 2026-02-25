# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install test dependencies:**
```bash
pip install -r requirements-test.txt
```

**Run all tests** (requires a running PostgreSQL instance):
```bash
pytest
```

**Run a single test file:**
```bash
pytest outputs/tests/test_models.py
```

**Run a single test:**
```bash
pytest outputs/tests/test_models.py::TestExportModel::test_something
```

Tests use `DJANGO_SETTINGS_MODULE=outputs.tests.settings` (set in `pytest.ini`). PostgreSQL connection defaults to `localhost:5432` with user/password `postgres` and database `test_db`; override with env vars `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

## Architecture

`django-outputs` is a reusable Django app providing data export and scheduled export functionality. It is distributed as a package (not a standalone project).

### Core Models (`outputs/models.py`)

- **`AbstractExport`** – Base model with shared fields (`content_type`, `format`, `context`, `exporter_path`, `fields`, `query_string`, `creator`, `recipients`).
- **`Export`** – Tracks a single export request with lifecycle status (`PENDING → PROCESSING → FINISHED/FAILED`). Items are stored via `ExportItem` and accessed through `export.object_list`.
- **`ExportItem`** – Join table linking an `Export` to individual object PKs (replaces former GM2M field). Stores per-item `result` and `detail`.
- **`Scheduler`** – Extends `AbstractExport` with cron scheduling via `django-rq` scheduler. Supports `DAILY`, `WEEKLY`, `MONTHLY`, and `CUSTOM` (cron string) routines.

### Exporter Mixins (`outputs/mixins.py`)

Exporters are built by combining mixins:

- **`ExporterMixin`** – Base for all exporters. Defines `export()`, `save_export()`, `export_to_response()`, and email delivery. `export_format` and `export_context` must be set on subclasses.
- **`FilterExporterMixin`** – Adds django-filter support. Set `queryset` and `filter_class` on the subclass; `get_queryset()` returns filtered results.
- **`ExcelExporterMixin`** – Inherits `ExporterMixin`. Uses `xlsxwriter` to generate XLSX. Subclasses must implement `selectable_fields()` (returns dict of field groups, each a list of `(attr, label, width[, format[, func]])` tuples) and `get_queryset()`. Supports `selectable_iterative_sets()` for repeated related-object columns. Writes in parallel pages using `ThreadPoolExecutor`.

A typical concrete exporter inherits `FilterExporterMixin` + `ExcelExporterMixin`.

### Export Flow

1. **Immediate export** (`ConfirmExportMixin` / `SelectExportMixin` views): `execute_export()` in `usecases.py` calls `exporter.save_export()` then `export.send_mail()`.
2. **Async processing** (`jobs.py`): `mail_export_by_id` is an RQ task (queue `exports`) that calls `export_items()` in `usecases.py`, which runs the exporter, updates `Export.status` and all `ExportItem.result` fields atomically, then emails recipients.
3. **Scheduled exports** (`cron.py`): `schedule_export()` is invoked by `rq-scheduler` via a cron job stored on the `Scheduler` model; it calls `execute_export()` with the scheduler's exporter.

### Configuration (`outputs/settings.py`)

All settings are optional Django project settings prefixed `OUTPUTS_`:

| Setting | Default | Purpose |
|---|---|---|
| `OUTPUTS_EXCLUDE_EXPORTERS` | `[]` | Exporter paths to hide |
| `OUTPUTS_EXPORTERS_MODULE_MAPPING` | `{}` | Maps model label + context to exporter module |
| `OUTPUTS_MIGRATION_DEPENDENCIES` | `[]` | Extra migration deps |
| `OUTPUTS_RELATED_MODELS` | `[]` | Related models for migrations |
| `OUTPUTS_NUMBER_OF_THREADS` | `4` | Threads for parallel XLSX writing |
| `OUTPUTS_SAVE_AS_FILE` | `False` | Save export file to storage instead of attaching to email |

### RQ Queues

The app expects three RQ queues defined in `RQ_QUEUES`: `default`, `cron`, and `exports`.

### Testing Patterns

- RQ and Redis are mocked via `fakeredis` and `monkeypatch` in `conftest.py`.
- `SampleModel` (defined in `outputs/tests/models.py`) is created dynamically in each test run via a `schema_editor`.
- `import_string` is globally patched to return `MockExporter` for any path containing `tests` and `Exporter`.
