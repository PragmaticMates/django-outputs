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

## Building an Exporter

Exporters are plain Python classes assembled from mixins. A typical XLSX list exporter:

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
                ('id',         'ID',     5),
                ('status',     'Status', 15),
                ('created',    'Date',   15, 'date'),
                ('total',      'Total',  12, 'money'),
            ]
        }
```

### Triggering an Export from a View

Use `ConfirmExportMixin` for a simple confirmation screen or `SelectExportMixin` to let the user pick which fields to export:

```python
from django.views.generic import FormView
from outputs.mixins import ConfirmExportMixin
from myapp.exporters import OrderExporter

class OrderExportView(ConfirmExportMixin, FormView):
    exporter_class = OrderExporter
    back_url = '/orders/'
```

### Overriding Queryset or Filter at Runtime

`FilterExporterMixin` accepts `queryset` and `filter_class` keyword arguments so you can override the defaults when constructing the exporter:

```python
exporter = OrderExporter(
    params=request.GET,
    queryset=Order.objects.filter(shop=request.user.shop),
    filter_class=ShopOrderFilter,
    user=request.user,
    recipients=[request.user],
)
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
