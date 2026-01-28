"""
Tests for jobs.
"""
import pytest
from unittest.mock import patch

from outputs.models import Export
from outputs.jobs import mail_export_by_id


class TestMailExportById:
    """Tests for mail_export_by_id job."""

    def test_mail_export_by_id_success(self, export, mock_rq_queue):
        """Test successful job execution."""
        with patch('outputs.jobs.import_string') as mock_import:
            mock_import.return_value = Export
            
            with patch('outputs.jobs.export_items') as mock_export_items:
                mail_export_by_id(
                    export.pk,
                    'outputs.models.Export',
                    'en',
                    'test.xlsx'
                )
                assert mock_export_items.called

    def test_mail_export_by_id_failure(self, export, mock_rq_queue):
        """Test job failure."""
        with patch('outputs.jobs.import_string') as mock_import:
            mock_import.return_value = Export
            
            with patch('outputs.jobs.export_items', side_effect=Exception('Export error')):
                with pytest.raises(Exception):
                    mail_export_by_id(
                        export.pk,
                        'outputs.models.Export',
                        'en'
                    )

    def test_mail_export_by_id_status_update(self, export, mock_rq_queue):
        """Test status update."""
        with patch('outputs.jobs.import_string') as mock_import:
            mock_import.return_value = Export
            
            with patch('outputs.jobs.export_items') as mock_export_items:
                mail_export_by_id(
                    export.pk,
                    'outputs.models.Export',
                    'en'
                )
                
                export.refresh_from_db()
                # Status should be updated to PROCESSING
                assert export.status == Export.STATUS_PROCESSING

    def test_mail_export_by_id_language(self, export, mock_rq_queue):
        """Test language activation."""
        with patch('outputs.jobs.import_string') as mock_import:
            mock_import.return_value = Export
            
            with patch('outputs.jobs.export_items') as mock_export_items:
                with patch('outputs.jobs.translation.activate') as mock_activate:
                    mail_export_by_id(
                        export.pk,
                        'outputs.models.Export',
                        'sk'
                    )
                    mock_activate.assert_called_with('sk')

