# django-outputs

A reusable Django app that provides asynchronous data exports and scheduled recurring exports. Exports are processed via [django-rq](https://github.com/rq/django-rq) and delivered to recipients by email.

## Features

- **Async exports** – Export data to XLSX, XML, or PDF; processing runs in an RQ worker and the result is emailed to recipients.
- **Scheduled exports** – Set up recurring exports (daily, weekly, monthly, or custom cron) using `rq-scheduler`.
- **Mixin-based exporters** – Compose exporters from provided mixins; supports field selection, django-filter integration, and parallel XLSX writing.
- **Export tracking** – Every export and its individual items are persisted in the database with status tracking.
- **Admin & views** – Ships with Django admin registrations and list/CRUD views for exports and schedulers.

## Quick start

```bash
pip install django-outputs
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    'outputs',
]
```

See [Installation](installation.md) for the full setup guide.

## License

GPLv3
