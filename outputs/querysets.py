from django.db import models


class ExportQuerySet(models.QuerySet):
    pass

class ExportItemQuerySet(models.QuerySet):
    def successful(self):
        return self.filter(result=self.model.RESULT_SUCCESS)

    def failed(self):
        return self.filter(result=self.model.RESULT_FAILURE)

    def for_object(self, object_id, content_type):
        return self.filter(object_id=object_id, content_type=content_type)

    def by_export_id(self, export_id):
        return self.filter(export__id=export_id)

class SchedulerQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)
