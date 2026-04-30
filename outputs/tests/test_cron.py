"""
Tests for cron functions.
"""
from unittest.mock import patch

from outputs.models import Scheduler
from outputs.cron import schedule_export
from outputs.jobs import execute_export


class TestScheduleExport:
    """Tests for schedule_export function."""

    def test_schedule_export_uses_dispatch_task(self, scheduler, mock_rq_queue):
        """schedule_export must use dispatch_task, not execute_export.delay."""
        with patch('outputs.cron.import_string') as mock_import, \
             patch('outputs.cron.dispatch_task') as mock_dispatch, \
             patch('outputs.cron.serialize_exporter_params', return_value={}) as mock_serialize:
            mock_import.return_value = Scheduler

            schedule_export(scheduler.pk, 'outputs.models.Scheduler')

        mock_dispatch.assert_called_once()
        # First arg must be the execute_export job function
        assert mock_dispatch.call_args[0][0] is execute_export
        assert mock_dispatch.call_args[0][1] == scheduler.exporter_class.get_path()

    def test_schedule_export_serializes_exporter_params(self, scheduler, mock_rq_queue):
        """schedule_export must call serialize_exporter_params before dispatching."""
        with patch('outputs.cron.import_string') as mock_import, \
             patch('outputs.cron.dispatch_task'), \
             patch('outputs.cron.serialize_exporter_params', return_value={}) as mock_serialize:
            mock_import.return_value = Scheduler

            schedule_export(scheduler.pk, 'outputs.models.Scheduler')

        mock_serialize.assert_called_once_with(scheduler.exporter_params)

    def test_schedule_export_passes_language(self, scheduler, mock_rq_queue):
        """Language from the scheduler is forwarded as a kwarg to dispatch_task."""
        with patch('outputs.cron.import_string') as mock_import, \
             patch('outputs.cron.dispatch_task') as mock_dispatch, \
             patch('outputs.cron.serialize_exporter_params', return_value={}):
            mock_import.return_value = Scheduler

            schedule_export(scheduler.pk, 'outputs.models.Scheduler')

        call_kwargs = mock_dispatch.call_args[1]
        assert call_kwargs.get('language') == scheduler.language

    def test_schedule_export_updates_executions(self, scheduler, mock_rq_queue):
        """Executions list is appended to after dispatching."""
        initial_count = len(scheduler.executions)

        with patch('outputs.cron.import_string') as mock_import, \
             patch('outputs.cron.dispatch_task'), \
             patch('outputs.cron.serialize_exporter_params', return_value={}):
            mock_import.return_value = Scheduler

            schedule_export(scheduler.pk, 'outputs.models.Scheduler')

        scheduler.refresh_from_db()
        assert len(scheduler.executions) == initial_count + 1
