"""
Tests for cron functions.
"""
from unittest.mock import Mock, patch

from outputs.models import Scheduler
from outputs.cron import schedule_export


class TestScheduleExport:
    """Tests for schedule_export function."""

    def test_schedule_export_calls_execute_export(self, scheduler, mock_rq_queue):
        """Test that schedule_export calls execute_export with correct arguments."""
        with patch('outputs.cron.import_string') as mock_import, \
             patch('outputs.usecases.execute_export') as mock_execute:
            mock_import.return_value = Scheduler

            schedule_export(scheduler.pk, 'outputs.models.Scheduler')

            mock_execute.assert_called_once()
            call_kwargs = mock_execute.call_args.kwargs
            assert call_kwargs['language'] == scheduler.language

    def test_schedule_export_passes_exporter_instance(self, scheduler, mock_rq_queue):
        """Test that schedule_export passes an exporter instance (not class) to execute_export."""
        with patch('outputs.cron.import_string') as mock_import, \
             patch('outputs.usecases.execute_export') as mock_execute:
            mock_import.return_value = Scheduler

            schedule_export(scheduler.pk, 'outputs.models.Scheduler')

            exporter_arg = mock_execute.call_args.args[0]
            # Should be an instance, not a class
            assert not isinstance(exporter_arg, type)

    def test_schedule_export_updates_executions(self, scheduler, mock_rq_queue):
        """Test that executions list is updated after export."""
        initial_executions_count = len(scheduler.executions)

        with patch('outputs.cron.import_string') as mock_import, \
             patch('outputs.usecases.execute_export'):
            mock_import.return_value = Scheduler

            schedule_export(scheduler.pk, 'outputs.models.Scheduler')

            scheduler.refresh_from_db()
            assert len(scheduler.executions) == initial_executions_count + 1
