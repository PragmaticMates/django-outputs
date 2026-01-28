"""
Tests for custom querysets.
"""
from django.contrib.contenttypes.models import ContentType

from outputs.models import ExportItem, Scheduler
from outputs.tests.models import SampleModel


class TestExportItemQuerySet:
    """Tests for ExportItemQuerySet."""

    def test_export_item_queryset_successful(self, export, test_model):
        """Test successful() filter."""
        content_type = ContentType.objects.get_for_model(SampleModel)
        ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk,
            result=ExportItem.RESULT_SUCCESS
        )
        ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk,
            result=ExportItem.RESULT_FAILURE
        )
        successful = ExportItem.objects.successful()
        assert successful.count() == 1
        assert successful.first().result == ExportItem.RESULT_SUCCESS

    def test_export_item_queryset_failed(self, export, test_model):
        """Test failed() filter."""
        content_type = ContentType.objects.get_for_model(SampleModel)
        ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk,
            result=ExportItem.RESULT_SUCCESS
        )
        ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk,
            result=ExportItem.RESULT_FAILURE
        )
        failed = ExportItem.objects.failed()
        assert failed.count() == 1
        assert failed.first().result == ExportItem.RESULT_FAILURE

    def test_export_item_queryset_for_object(self, export, test_model):
        """Test for_object() filter."""
        content_type = ContentType.objects.get_for_model(SampleModel)
        item = ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk,
            result=ExportItem.RESULT_SUCCESS
        )
        found = ExportItem.objects.for_object(test_model.pk, content_type)
        assert found.count() == 1
        assert found.first() == item

    def test_export_item_queryset_by_export_id(self, export, test_model):
        """Test by_export_id() filter."""
        content_type = ContentType.objects.get_for_model(SampleModel)
        item = ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk,
            result=ExportItem.RESULT_SUCCESS
        )
        found = ExportItem.objects.by_export_id(export.pk)
        assert found.count() == 1
        assert found.first() == item


class TestSchedulerQuerySet:
    """Tests for SchedulerQuerySet."""

    def test_scheduler_queryset_active(self, scheduler):
        """Test active() filter."""
        scheduler.is_active = True
        scheduler.save()
        
        inactive_scheduler = Scheduler.objects.create(
            content_type=scheduler.content_type,
            format=scheduler.format,
            context=scheduler.context,
            routine=scheduler.routine,
            creator=scheduler.creator,
            is_active=False
        )
        
        active = Scheduler.objects.active()
        assert active.count() == 1
        assert active.first() == scheduler
        assert inactive_scheduler not in active

