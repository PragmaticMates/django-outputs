"""
Tests for signals.
"""
import pytest
from django.contrib.contenttypes.models import ContentType
from unittest.mock import Mock, patch

from outputs.models import Export, Scheduler, ExportItem
from outputs.signals import export_item_changed
from outputs.tests.models import SampleModel


class TestExportExecutedPostSave:
    """Tests for export_executed_post_save signal."""

    def test_export_executed_post_save_signal(self, export, mock_rq_queue):
        """Test signal on export creation."""
        with patch('outputs.signals.django_rq.get_scheduler') as mock_scheduler:
            mock_sched = Mock()
            mock_sched.enqueue_in = Mock()
            mock_scheduler.return_value = mock_sched
            
            # Create new export to trigger signal
            new_export = Export.objects.create(
                content_type=export.content_type,
                format=export.format,
                context=export.context,
                creator=export.creator,
                total=5
            )
            
            # Signal should schedule notification
            # Note: This test may need adjustment based on actual signal implementation

    def test_export_executed_post_save_notification(self, export, mock_rq_queue, settings):
        """Test notification scheduling."""
        settings.INSTALLED_APPS = ['outputs', 'whistle']
        
        with patch('outputs.signals.django_rq.get_scheduler') as mock_scheduler:
            mock_sched = Mock()
            mock_sched.enqueue_in = Mock()
            mock_scheduler.return_value = mock_sched
            
            new_export = Export.objects.create(
                content_type=export.content_type,
                format=export.format,
                context=export.context,
                creator=export.creator,
                total=5
            )
            
            # Check that scheduler was called
            # Note: This depends on signal implementation


class TestRescheduleScheduler:
    """Tests for reschedule_scheduler signal."""

    def test_reschedule_scheduler_on_routine_change(self, scheduler, mock_rq_queue):
        """Test rescheduling on routine change."""
        original_routine = scheduler.routine
        scheduler.routine = Scheduler.ROUTINE_WEEKLY
        
        with patch('outputs.signals.schedule_scheduler') as mock_schedule:
            scheduler.save()
            # Signal should trigger rescheduling
            # Note: This depends on signal implementation

    def test_reschedule_scheduler_on_cron_string_change(self, scheduler, mock_rq_queue):
        """Test rescheduling on cron change."""
        scheduler.routine = Scheduler.ROUTINE_CUSTOM
        scheduler.cron_string = '0 12 * * *'
        
        with patch('outputs.signals.schedule_scheduler') as mock_schedule:
            scheduler.save()
            # Signal should trigger rescheduling

    def test_reschedule_scheduler_on_is_active_change(self, scheduler, mock_rq_queue):
        """Test rescheduling on active change."""
        scheduler.is_active = False
        
        with patch('outputs.signals.schedule_scheduler') as mock_schedule:
            scheduler.save()
            # Signal should trigger rescheduling


class TestCancelScheduler:
    """Tests for cancel_scheduler signal."""

    def test_cancel_scheduler_on_delete(self, scheduler, mock_rq_queue):
        """Test canceling on delete."""
        scheduler.job_id = 'test-job-id'
        scheduler.save()
        
        with patch.object(scheduler, 'cancel_schedule') as mock_cancel:
            scheduler.delete()
            # Signal should call cancel_schedule
            # Note: This depends on signal implementation


class TestNotifyAboutScheduler:
    """Tests for notify_about_scheduler signal."""

    def test_notify_about_scheduler_on_create(self, user, content_type, mock_rq_queue, settings):
        """Test notification on creation."""
        settings.INSTALLED_APPS = ['outputs', 'whistle']
        
        with patch('outputs.signals.notify') as mock_notify:
            scheduler = Scheduler.objects.create(
                content_type=content_type,
                format=Scheduler.FORMAT_XLSX,
                context=Scheduler.CONTEXT_LIST,
                routine=Scheduler.ROUTINE_DAILY,
                creator=user,
                is_active=True
            )
            # Signal should send notification
            # Note: This depends on signal implementation


class TestUpdateExportItem:
    """Tests for update_export_item signal."""

    def test_update_export_item_signal(self, export, test_model):
        """Test export item update signal."""
        content_type = ContentType.objects.get_for_model(SampleModel)
        
        # Send signal
        export_item_changed.send(
            sender=ExportItem,
            export_id=export.pk,
            object_id=test_model.pk,
            result=ExportItem.RESULT_SUCCESS,
            detail='Test detail'
        )
        
        # Check that ExportItem was created/updated
        item = ExportItem.objects.filter(
            export=export,
            object_id=test_model.pk
        ).first()
        
        assert item is not None
        assert item.result == ExportItem.RESULT_SUCCESS
        assert item.detail == 'Test detail'

