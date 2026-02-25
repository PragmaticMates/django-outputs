# Installation

## Requirements

- Python 3.5+
- Django 4.2+
- PostgreSQL (uses `ArrayField`)
- Redis (for RQ queues)

## Install the package

```bash
pip install django-outputs
```

## Configure Django

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

## Settings

All settings are optional and are read from your Django project settings:

| Setting | Default | Description |
|---|---|---|
| `OUTPUTS_EXCLUDE_EXPORTERS` | `[]` | List of exporter dotted paths to hide from admin/UI |
| `OUTPUTS_EXPORTERS_MODULE_MAPPING` | `{}` | Maps `ModelLabel` + context to exporter module (used for statistics/detail contexts) |
| `OUTPUTS_MIGRATION_DEPENDENCIES` | `[]` | Extra migration dependencies to add |
| `OUTPUTS_RELATED_MODELS` | `[]` | Related models |
| `OUTPUTS_NUMBER_OF_THREADS` | `4` | Worker threads for parallel XLSX page writing |
| `OUTPUTS_SAVE_AS_FILE` | `False` | Save export file to Django's default storage instead of attaching it to email |

## Optional integrations

- **`django-whistle`** – When installed, sends in-app notifications on export failure, export execution, and scheduler creation.
- **`django-auditlog`** – When installed, audit history is recorded for `Export` and `Scheduler` models.

## Running tests

```bash
pip install -r requirements-test.txt
pytest
```

Tests require a running PostgreSQL instance. Connection defaults can be overridden with environment variables: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
