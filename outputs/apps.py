from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class OutputsConfig(AppConfig):
    name = 'outputs'
    verbose_name = _('Outputs')

    def schedule_jobs(self):
        from outputs.models import Scheduler

        for output_scheduler in Scheduler.objects.active():
            output_scheduler.schedule()
