"""
Tests for cron functions.
"""
import pytest
from unittest.mock import Mock, patch
from django.utils import timezone

from outputs.models import Scheduler
from outputs.cron import schedule_export


class TestScheduleExport:
    """Tests for schedule_export function."""

    def test_schedule_export_execution(self, scheduler, mock_rq_queue):
        """Test export execution."""
        with patch('outputs.cron.import_string') as mock_import:
            mock_import.return_value = Scheduler
            
            with patch('outputs.cron.jobs') as mock_jobs:
                mock_jobs.execute_export.delay = Mock()
                
                schedule_export(scheduler.pk, 'outputs.models.Scheduler')
                
                assert mock_jobs.execute_export.delay.called

    def test_schedule_export_executions_update(self, scheduler, mock_rq_queue):
        """Test executions list update."""
        initial_executions_count = len(scheduler.executions)
        
        with patch('outputs.cron.import_string') as mock_import:
            mock_import.return_value = Scheduler
            
            with patch('outputs.cron.jobs') as mock_jobs:
                mock_jobs.execute_export.delay = Mock()
                
                schedule_export(scheduler.pk, 'outputs.models.Scheduler')
                
                scheduler.refresh_from_db()
                assert len(scheduler.executions) == initial_executions_count + 1

    def test_schedule_export_job_delay(self, scheduler, mock_rq_queue):
        """Test job delay."""
        with patch('outputs.cron.import_string') as mock_import:
            mock_import.return_value = Scheduler
            
            with patch('outputs.cron.jobs') as mock_jobs:
                mock_jobs.execute_export.delay = Mock()
                
                schedule_export(scheduler.pk, 'outputs.models.Scheduler')
                
                # Check that delay was called with correct arguments
                assert mock_jobs.execute_export.delay.called
                call_args = mock_jobs.execute_export.delay.call_args
                assert 'language' in call_args.kwargs
                assert call_args.kwargs['language'] == scheduler.language

