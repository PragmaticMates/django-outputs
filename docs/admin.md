# Admin

All three models are registered in `outputs.admin`.

## `ExportAdmin`

- **List display**: id, content type, output type, format, context, exporter path, status, creator, total items, created date.
- **Filters**: status, output type, format, context, content type, and a custom `ExportedWithExporterListFilter` that lists all registered exporter classes (subclasses of `ExporterMixin` not ending in `Mixin`, minus any in `OUTPUTS_EXCLUDE_EXPORTERS`).
- **Search**: creator first/last name.
- **Actions**: *Send mail* – re-sends the export email for selected records using the request's current language.
- **View on site**: links to `export.get_absolute_url()`.
- `total`, `created`, and `modified` are read-only.

## `ExportItemAdmin`

- **List display**: id, export (linked to the Export change page), content type, output type, object id, result, truncated detail (100 chars), created date.
- **Filters**: result, created date, export output type.
- **Search**: export id, object id.
- All fields are read-only; the record is a pure audit trail.
- `show_full_result_count = False` to avoid expensive `COUNT(*)` on large tables.

## `SchedulerAdmin`

- **List display**: id, is_active, routine, cron_string, cron_description, content type, format, creator, created date.
- **Filters**: routine, is_active, format, context, content type.
- **Search**: creator first/last name.

## `get_exporter_path_choices()`

A module-level helper function that introspects the `ExporterMixin` class hierarchy at runtime to build a list of `(dotted_path, label)` tuples for all registered concrete exporters. It excludes classes whose names end with `Mixin` and any paths listed in `OUTPUTS_EXCLUDE_EXPORTERS`. Labels come from `ExporterMixin.get_description()`.

This function is used internally by `ExportedWithExporterListFilter` and is also available for use in your own forms or admin filters.
