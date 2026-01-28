"""
Tests for cron functions.
"""
import sys
from unittest.mock import Mock, patch, MagicMock

from outputs.models import Scheduler
from outputs.cron import schedule_export


class TestScheduleExport:
    """Tests for schedule_export function."""

    def test_schedule_export_execution(self, scheduler, mock_rq_queue):
        """Test export execution."""
        with patch('outputs.cron.import_string') as mock_import:
            mock_import.return_value = Scheduler
            
            # cron.py does 'from outputs import jobs' inside the function
            # We need to create a mock module and patch it in sys.modules
            mock_jobs_module = MagicMock()
            mock_execute_export = Mock()
            mock_execute_export.delay = Mock()
            mock_jobs_module.execute_export = mock_execute_export
            
            # Patch the outputs module to have jobs attribute
            original_outputs = sys.modules.get('outputs')
            mock_outputs = MagicMock()
            mock_outputs.jobs = mock_jobs_module
            sys.modules['outputs'] = mock_outputs
            
            try:
                schedule_export(scheduler.pk, 'outputs.models.Scheduler')
            finally:
                if original_outputs:
                    sys.modules['outputs'] = original_outputs
            
            assert mock_execute_export.delay.called

    def test_schedule_export_executions_update(self, scheduler, mock_rq_queue):
        """Test executions list update."""
        initial_executions_count = len(scheduler.executions)
        
        with patch('outputs.cron.import_string') as mock_import:
            mock_import.return_value = Scheduler
            
            # cron.py does 'from outputs import jobs' inside the function
            # We need to create a mock module and patch it in sys.modules
            mock_jobs_module = MagicMock()
            mock_execute_export = Mock()
            mock_execute_export.delay = Mock()
            mock_jobs_module.execute_export = mock_execute_export
            
            # Patch the outputs module to have jobs attribute
            original_outputs = sys.modules.get('outputs')
            mock_outputs = MagicMock()
            mock_outputs.jobs = mock_jobs_module
            sys.modules['outputs'] = mock_outputs
            
            try:
                schedule_export(scheduler.pk, 'outputs.models.Scheduler')
            finally:
                if original_outputs:
                    sys.modules['outputs'] = original_outputs
            
            scheduler.refresh_from_db()
            assert len(scheduler.executions) == initial_executions_count + 1

    def test_schedule_export_job_delay(self, scheduler, mock_rq_queue):
        """Test job delay."""
        with patch('outputs.cron.import_string') as mock_import:
            mock_import.return_value = Scheduler
            
            # cron.py does 'from outputs import jobs' inside the function
            # We need to create a mock module and patch it in sys.modules
            mock_jobs_module = MagicMock()
            mock_execute_export = Mock()
            mock_execute_export.delay = Mock()
            mock_jobs_module.execute_export = mock_execute_export
            
            # Patch the outputs module to have jobs attribute
            original_outputs = sys.modules.get('outputs')
            mock_outputs = MagicMock()
            mock_outputs.jobs = mock_jobs_module
            sys.modules['outputs'] = mock_outputs
            
            try:
                schedule_export(scheduler.pk, 'outputs.models.Scheduler')
            finally:
                if original_outputs:
                    sys.modules['outputs'] = original_outputs
            
            # Check that delay was called with correct arguments
            assert mock_execute_export.delay.called
            call_args = mock_execute_export.delay.call_args
            assert 'language' in call_args.kwargs
            assert call_args.kwargs['language'] == scheduler.language

