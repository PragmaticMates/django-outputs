# django-outputs

A reusable Django app that provides asynchronous data exports and scheduled recurring exports. Exports are processed via [django-rq](https://github.com/rq/django-rq) and delivered to recipients by email.

## Features

- **Async exports** – Export data to XLSX, XML, or PDF; processing runs in an RQ worker and the result is emailed to recipients.
- **Scheduled exports** – Set up recurring exports (daily, weekly, monthly, or custom cron) using `rq-scheduler`.
- **Mixin-based exporters** – Compose exporters from provided mixins; supports field selection, django-filter integration, and parallel XLSX writing.
- **Export tracking** – Every export and its individual items are persisted in the database with status tracking.
- **Admin & views** – Ships with Django admin registrations and list/CRUD views for exports and schedulers.

## Requirements

- Python 3.5+
- Django 4.2+
- PostgreSQL (uses `ArrayField`)
- Redis (for RQ queues)

## Installation

```bash
pip install django-outputs
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    'outputs',
]
```

Include the URLs:

```python
# urls.py
urlpatterns = [
    ...
    path('', include('outputs.urls', namespace='outputs')),
]
```

Configure three RQ queues in your settings:

```python
RQ_QUEUES = {
    'default': {'HOST': 'localhost', 'PORT': 6379, 'DB': 0},
    'exports': {'HOST': 'localhost', 'PORT': 6379, 'DB': 0, 'DEFAULT_TIMEOUT': 360},
    'cron':    {'HOST': 'localhost', 'PORT': 6379, 'DB': 0, 'DEFAULT_TIMEOUT': 360},
}
```

Run migrations:

```bash
python manage.py migrate
```

## Configuration

All settings are optional and are read from your Django project settings:

| Setting | Default | Description |
|---|---|---|
| `OUTPUTS_EXCLUDE_EXPORTERS` | `[]` | List of exporter dotted paths to hide from admin/UI |
| `OUTPUTS_EXPORTERS_MODULE_MAPPING` | `{}` | Maps `ModelLabel` + context to exporter module (used for statistics/detail contexts) |
| `OUTPUTS_MIGRATION_DEPENDENCIES` | `[]` | Extra migration dependencies to add |
| `OUTPUTS_RELATED_MODELS` | `[]` | Related models |
| `OUTPUTS_NUMBER_OF_THREADS` | `4` | Worker threads for parallel XLSX page writing |
| `OUTPUTS_SAVE_AS_FILE` | `False` | Save export file to Django's default storage instead of attaching it to email |

## Mixins

All mixins live in `outputs.mixins`. Exporters are assembled by combining them; views gain export behaviour the same way.

### Exporter mixins

#### `ExporterMixin`

The base for every exporter. It initialises an in-memory `BytesIO` output stream and provides the scaffolding that the rest of the system depends on.

Class attributes to set on subclasses:

| Attribute | Default | Description |
|---|---|---|
| `filename` | `None` | Output filename (accents are stripped automatically) |
| `description` | `''` | Human-readable label shown in admin; auto-generated from model/format/context if empty |
| `export_format` | `None` | One of `Export.FORMAT_XLSX`, `FORMAT_XML`, `FORMAT_PDF` |
| `export_context` | `None` | One of `Export.CONTEXT_LIST`, `CONTEXT_STATISTICS`, `CONTEXT_DETAIL` |
| `output_type` | `FILE` | `Export.OUTPUT_TYPE_FILE` or `OUTPUT_TYPE_STREAM` |
| `send_separately` | `False` | Send one email per recipient instead of a single email to all |
| `content_type` | `application/force-download` | HTTP content-type / MIME type of the output |

Key methods to implement or override:

- **`export()`** – Generate output and write it to `self.output`.
- **`write_data(output)`** – Called by `export()`; receives the format-specific output object (e.g. xlsxwriter worksheet).
- **`get_message_body(count, file_url=None)`** – Return the HTML email body sent to recipients.
- **`get_message_subject()`** – Return a custom email subject, or `None` to use the default.
- **`export_to_response()`** – Calls `export()` and returns an `HttpResponse` with the file attached; useful for synchronous streaming exports.
- **`save_export()`** – Persists an `Export` record and `ExportItem` records to the database; called by `execute_export()` before enqueuing the mail job.

---

#### `FilterExporterMixin`

Adds [django-filter](https://django-filter.readthedocs.io/) support so the exported queryset matches whatever filters the user applied in the UI.

Class attributes:

| Attribute | Description |
|---|---|
| `queryset` | Base queryset for the model being exported |
| `filter_class` | A `django_filters.FilterSet` subclass |
| `model` | Alternative to `queryset` when only a model reference is needed |

Both `queryset` and `filter_class` can be overridden at instantiation time by passing them as keyword arguments, which lets a single exporter class serve multiple filtered views:

```python
exporter = OrderExporter(
    params=request.GET,
    queryset=Order.objects.filter(shop=request.user.shop),
    filter_class=ShopOrderFilter,
    user=request.user,
    recipients=[request.user],
)
```

`get_queryset()` returns the filter's queryset. If an `items` list is passed (e.g. when re-sending a previously saved export), it restricts the queryset to those PKs instead of re-applying the filter.

If the query string contains a `proxy` parameter, `get_whole_queryset()` calls `.proxy(proxy)` on the queryset, enabling proxy-model-scoped exports.

`get_message_body()` renders `outputs/export_message_body.html` and passes the active filter's human-readable field values into the template context.

---

#### `ExcelExporterMixin`

Extends `ExporterMixin` to produce XLSX files via [xlsxwriter](https://xlsxwriter.readthedocs.io/). Sets `export_format = FORMAT_XLSX` and `export_context = CONTEXT_LIST` by default.

Subclasses **must** implement:

- **`selectable_fields()`** *(static)* – Returns a dict of `{ group_label: [field_tuple, ...] }`. Each field tuple is:
  ```
  (attribute, header_label, column_width [, cell_format [, transform_func]])
  ```
  - `attribute` – dotted attribute path on the object, e.g. `'customer.name'`. A `[key]` suffix reads from a dict: `'metadata[color]'`.
  - `cell_format` – optional key into the built-in format table (see below).
  - `transform_func` – optional callable `func(value[, obj])` applied after attribute lookup. Return a `(formula_string, fallback_value)` tuple to write an Excel formula.
- **`get_worksheet_title(index=0)`** – Returns the worksheet tab name.
- **`get_queryset()`** – Returns the queryset to export (typically delegated to `FilterExporterMixin`).

Optional:

- **`selectable_iterative_sets()`** – Returns a dict of `{ related_manager_attr: { group_label: [field_tuple, ...] } }`. Used to expand one-to-many relationships into repeated column groups (e.g. order lines). The number of column groups is determined dynamically from the object with the most related records.
- **`header_update`** (dict) – Override column headers at the instance level without changing `selectable_fields()`. Keys are attribute names; values are replacement labels. For iterative sets, the value is itself a dict of `{ attr: label }`.
- **`proxy_class`** – If set, each object's `__class__` is reassigned to this proxy class before reading attributes, enabling method dispatch on a proxy model.

Built-in cell formats (pass as the 4th element of a field tuple):

| Key | Format |
|---|---|
| `bold` | Bold text |
| `header` | Bold white text on red background (used for the header row automatically) |
| `date` | `dd.mm.yyyy` |
| `datetime` | `dd.mm.yyyy hh:mm` |
| `time` | `hh:mm` |
| `integer` | No decimal places |
| `percent` | `0.00%` |
| `money` | `### ### ##0.00 €` |
| `bold_money` | Same as `money` but bold |
| `money_amount` | `### ### ##0.00` (no currency symbol) |
| `bold_money_amount` | Same as `money_amount` but bold |

Content is written in parallel using `ThreadPoolExecutor` (controlled by `OUTPUTS_NUMBER_OF_THREADS`) when the queryset is large enough. The worksheet gets autofilter and frozen header row applied automatically.

---

### View mixins

#### `ConfirmExportMixin`

Adds a confirmation step to any `FormView`. Renders `outputs/export_confirmation.html`, which shows the number of records that will be exported and a "confirm" button. On submit it triggers the async export and displays a flash message.

```python
from django.views.generic import FormView
from outputs.mixins import ConfirmExportMixin
from myapp.exporters import OrderExporter

class OrderExportView(ConfirmExportMixin, FormView):
    exporter_class = OrderExporter
    back_url = '/orders/'   # fallback; can also be passed via ?back_url= GET param
```

The `back_url` is resolved from the `back_url` GET parameter first, then from the class attribute. It is passed to the template as context and used as the success redirect URL.

Override `exporter_params` (property) to customise the keyword arguments forwarded to the exporter constructor.

---

#### `SelectExportMixin`

Extends `ConfirmExportMixin` with a field-selection step. Uses `ChooseExportFieldsForm` and renders `outputs/export_selection.html`. The form is populated from the exporter's `selectable_fields()` and `selectable_iterative_sets()`.

```python
from outputs.mixins import SelectExportMixin
from myapp.exporters import OrderExporter

class OrderSelectExportView(SelectExportMixin, FormView):
    exporter_class = OrderExporter
    back_url = '/orders/'
```

Field visibility is permission-controlled: superusers see every field; regular users see only the fields permitted by their `export_fields_permissions` user attribute and by the `export_fields_permissions` JSON stored on their group metadata.

---

#### `ExportFieldsPermissionsMixin`

A helper mixin used internally by `SelectExportMixin` to manage per-user/per-group field permissions. Permissions are stored as JSON dictionaries keyed by exporter dotted path, with lists of allowed field attribute names as values.

Useful methods if you need to manipulate permissions programmatically:

- **`load_export_fields_permissions(permissions)`** – Accepts a string, list, or queryset of raw JSON permission values and returns a list of parsed dicts.
- **`combine_export_fields_permissions(permissions)`** – Merges a list of permission dicts into a single dict (union of all allowed fields per exporter).
- **`substract_export_fields_permissions(first, second)`** – Returns `first − second`: fields allowed in `first` but not in `second`.

---

## Building an Exporter

A typical XLSX list exporter combining `FilterExporterMixin` and `ExcelExporterMixin`:

```python
import django_filters
from outputs.mixins import FilterExporterMixin, ExcelExporterMixin
from myapp.models import Order

class OrderFilter(django_filters.FilterSet):
    class Meta:
        model = Order
        fields = ['status', 'created']

class OrderExporter(FilterExporterMixin, ExcelExporterMixin):
    filename = 'orders.xlsx'
    description = 'Orders export'
    queryset = Order.objects.all()
    filter_class = OrderFilter

    def get_worksheet_title(self, index=0):
        return 'Orders'

    @staticmethod
    def selectable_fields():
        return {
            'Order': [
                # (attribute, header label, column width[, cell format[, transform func]])
                ('id',              'ID',       5),
                ('status',          'Status',   15),
                ('created',         'Date',     15, 'date'),
                ('total',           'Total',    12, 'money'),
                ('customer.name',   'Customer', 20),
                # transform function: receives (value, obj) or just (value,)
                ('is_paid', 'Paid', 8, None, lambda v: 'Yes' if v else 'No'),
            ]
        }
```

### Iterative sets (one-to-many columns)

When an object has a variable number of related records (e.g. order lines), define `selectable_iterative_sets()` to expand them into repeated column groups. The number of groups is determined automatically from the object with the most relations:

```python
@staticmethod
def selectable_iterative_sets():
    return {
        'lines_set': {   # related manager attribute name
            'Order line': [
                ('product.name', 'Product', 20),
                ('quantity',     'Qty',      6, 'integer'),
                ('price',        'Price',   12, 'money'),
            ]
        }
    }
```

## Scheduled Exports

A `Scheduler` instance wraps any exporter and triggers it on a cron schedule. Schedulers can be created:

- Via the Django admin
- Via the UI at `outputs:scheduler_create`
- Directly from an existing `Export` at `outputs:scheduler_create_from_export`

Routine choices: `DAILY` (08:00), `WEEKLY` (Monday 08:00), `MONTHLY` (1st of month 08:00), or `CUSTOM` (arbitrary cron string).

The scheduler job is managed automatically: creating, activating, deactivating, or deleting a `Scheduler` record updates the corresponding `rq-scheduler` cron job via Django signals.

## Optional Integrations

- **`django-whistle`** – When installed, sends in-app notifications on export failure and scheduler creation.
- **`django-auditlog`** – When installed, audit history is recorded for `Export` and `Scheduler` models.

## Running Tests

```bash
pip install -r requirements-test.txt
pytest
```

Tests require a running PostgreSQL instance. Connection defaults can be overridden with environment variables: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

## License

GPLv3
