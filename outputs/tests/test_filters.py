"""
Tests for filters.
"""
from django.utils import timezone
from datetime import timedelta

from outputs.filters import ExportFilter, SchedulerFilter
from outputs.models import Export, Scheduler


class TestExportFilter:
    """Tests for ExportFilter."""

    def test_export_filter_by_creator(self, export, user):
        """Test filtering by creator."""
        filter_obj = ExportFilter({'creator': user.pk}, queryset=Export.objects.all())
        assert export in filter_obj.qs

    def test_export_filter_by_content_type(self, export, content_type):
        """Test filtering by content type."""
        filter_obj = ExportFilter({'content_type': content_type.pk}, queryset=Export.objects.all())
        assert export in filter_obj.qs

    def test_export_filter_by_status(self, export):
        """Test filtering by status."""
        filter_obj = ExportFilter({'status': Export.STATUS_PENDING}, queryset=Export.objects.all())
        assert export in filter_obj.qs

    def test_export_filter_by_format(self, export):
        """Test filtering by format."""
        filter_obj = ExportFilter({'format': Export.FORMAT_XLSX}, queryset=Export.objects.all())
        assert export in filter_obj.qs

    def test_export_filter_by_context(self, export):
        """Test filtering by context."""
        filter_obj = ExportFilter({'context': Export.CONTEXT_LIST}, queryset=Export.objects.all())
        assert export in filter_obj.qs

    def test_export_filter_by_total_range(self, export):
        """Test filtering by total range."""
        filter_obj = ExportFilter({'total': '5,15'}, queryset=Export.objects.all())
        # Export has total=10, should be in range
        assert export in filter_obj.qs

    def test_export_filter_by_created_range(self, export):
        """Test filtering by created date range."""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        filter_obj = ExportFilter({
            'created': f'{yesterday},{tomorrow}'
        }, queryset=Export.objects.all())
        assert export in filter_obj.qs


class TestSchedulerFilter:
    """Tests for SchedulerFilter."""

    def test_scheduler_filter_by_creator(self, scheduler, user):
        """Test filtering by creator."""
        filter_obj = SchedulerFilter({'creator': user.pk}, queryset=Scheduler.objects.all())
        assert scheduler in filter_obj.qs

    def test_scheduler_filter_by_content_type(self, scheduler, content_type):
        """Test filtering by content type."""
        filter_obj = SchedulerFilter({'content_type': content_type.pk}, queryset=Scheduler.objects.all())
        assert scheduler in filter_obj.qs

    def test_scheduler_filter_by_routine(self, scheduler):
        """Test filtering by routine."""
        filter_obj = SchedulerFilter({'routine': Scheduler.ROUTINE_DAILY}, queryset=Scheduler.objects.all())
        assert scheduler in filter_obj.qs

    def test_scheduler_filter_by_is_active(self, scheduler):
        """Test filtering by active status."""
        filter_obj = SchedulerFilter({'is_active': 'True'}, queryset=Scheduler.objects.all())
        assert scheduler in filter_obj.qs

    def test_scheduler_filter_by_format(self, scheduler):
        """Test filtering by format."""
        filter_obj = SchedulerFilter({'format': Scheduler.FORMAT_XLSX}, queryset=Scheduler.objects.all())
        assert scheduler in filter_obj.qs

    def test_scheduler_filter_by_context(self, scheduler):
        """Test filtering by context."""
        filter_obj = SchedulerFilter({'context': Scheduler.CONTEXT_LIST}, queryset=Scheduler.objects.all())
        assert scheduler in filter_obj.qs

    def test_scheduler_filter_by_created_range(self, scheduler):
        """Test filtering by created date range."""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        filter_obj = SchedulerFilter({
            'created': f'{yesterday},{tomorrow}'
        }, queryset=Scheduler.objects.all())
        assert scheduler in filter_obj.qs

