from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _
from django.db.utils import ProgrammingError


class OutputsConfig(AppConfig):
    name = 'outputs'
    verbose_name = _('Outputs')

    def ready(self):
        try:
            self.schedule_jobs()
        except ProgrammingError:
            pass

    def schedule_jobs(self):
        print('Scheduling outputs jobs...')
        from outputs.models import Scheduler

        for output_scheduler in Scheduler.objects.active():
            output_scheduler.schedule()
