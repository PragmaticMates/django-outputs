from django.db import models


class ExportQuerySet(models.QuerySet):
    pass


class SchedulerQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)
