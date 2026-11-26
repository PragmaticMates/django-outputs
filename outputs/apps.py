from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OutputsConfig(AppConfig):
    name = 'outputs'
    # Export and Scheduler were created with AutoField: keep that whatever the
    # project's DEFAULT_AUTO_FIELD is, so it never asks for a migration.
    default_auto_field = 'django.db.models.AutoField'
    verbose_name = _('Outputs')

    def schedule_jobs(self):
        from outputs.models import Scheduler

        for output_scheduler in Scheduler.objects.active():
            output_scheduler.schedule()
