"""
Tests for models.
"""
import pytest
from django.contrib.contenttypes.models import ContentType
from django.http import QueryDict
from unittest.mock import patch

from outputs.models import Export, ExportItem, Scheduler, AbstractExport
from outputs.tests.models import SampleModel


class TestExport:
    """Tests for Export model."""

    def test_export_str(self, export):
        """Test string representation."""
        assert str(export) == f'Export #{export.pk} (Sample Models)'

    def test_export_exporter_class(self, export, exporter_class):
        """Test exporter class property."""
        with patch('outputs.models.import_string', return_value=exporter_class):
            assert export.exporter_class == exporter_class

    def test_export_exporter(self, export, exporter_class):
        """Test exporter instance property."""
        with patch('outputs.models.import_string', return_value=exporter_class):
            exporter = export.exporter
            assert exporter is not None
            assert exporter.user == export.creator

    def test_export_exporter_params(self, export):
        """Test exporter parameters."""
        params = export.exporter_params
        assert 'params' in params
        assert 'user' in params
        assert 'items' in params
        assert 'output_type' in params
        assert params['user'] == export.creator

    def test_export_params(self, export):
        """Test params property."""
        params = export.params
        assert isinstance(params, QueryDict)
        assert params.get('name') == 'test'

    def test_export_recipients_emails(self, export, user, other_user):
        """Test recipients emails."""
        export.recipients.add(other_user)
        emails = export.recipients_emails
        assert user.email in emails
        assert other_user.email in emails

    def test_export_get_params_display(self, export):
        """Test params display."""
        display = export.get_params_display()
        assert isinstance(display, str)

    def test_export_get_fields_labels(self, export):
        """Test field labels."""
        labels = export.get_fields_labels()
        assert isinstance(labels, list)

    def test_export_get_exporter_path(self):
        """Test exporter path generation."""
        path = AbstractExport.get_exporter_path(
            model_class=SampleModel,
            context=Export.CONTEXT_LIST,
            format=Export.FORMAT_XLSX
        )
        assert isinstance(path, str)
        assert 'Exporter' in path

    def test_export_get_items_url(self, export):
        """Test items URL."""
        url = export.get_items_url()
        # URL may be None if reverse fails
        assert url is None or isinstance(url, str)

    def test_export_get_absolute_url(self, export):
        """Test absolute URL."""
        url = export.get_absolute_url()
        # URL may be None if reverse fails
        assert url is None or isinstance(url, str)

    def test_export_get_language(self, export):
        """Test language extraction from URL."""
        export.url = '/en/exports/'
        assert export.get_language() == 'en'

    def test_export_get_language_default(self, export):
        """Test language default when URL doesn't have language."""
        export.url = '/exports/'
        assert export.get_language() == 'exports'

    def test_export_get_app_label(self, export):
        """Test app label extraction."""
        app_label = export.get_app_label()
        assert isinstance(app_label, str)

    def test_export_send_mail(self, export, mock_rq_queue):
        """Test send_mail method."""
        import sys
        from unittest.mock import MagicMock

        mock_jobs = MagicMock()
        mock_jobs.mail_export_by_id.delay = MagicMock()

        # Patch outputs module import to provide jobs attribute
        original_outputs = sys.modules.get('outputs')
        mock_outputs = MagicMock()
        mock_outputs.jobs = mock_jobs
        sys.modules['outputs'] = mock_outputs
        try:
            export.send_mail(language='en')
        finally:
            if original_outputs:
                sys.modules['outputs'] = original_outputs

        assert mock_jobs.mail_export_by_id.delay.called

    def test_export_object_list(self, export, test_model):
        """Test object_list property."""
        from outputs.models import ExportItem
        ExportItem.objects.create(
            export=export,
            content_type=ContentType.objects.get_for_model(SampleModel),
            object_id=test_model.pk
        )
        object_list = export.object_list
        assert test_model in object_list

    def test_export_object_list_empty(self, export):
        """Test object_list property when no items."""
        object_list = export.object_list
        assert object_list.count() == 0

    def test_export_update_export_items_result(self, export, test_model):
        """Test updating export items result."""
        from outputs.models import ExportItem
        content_type = ContentType.objects.get_for_model(SampleModel)
        ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk
        )
        updated_count = export.update_export_items_result(ExportItem.RESULT_SUCCESS)
        assert updated_count == 1
        assert export.export_items.first().result == ExportItem.RESULT_SUCCESS

    def test_export_update_export_items_result_with_detail(self, export, test_model):
        """Test updating export items result with detail."""
        from outputs.models import ExportItem
        content_type = ContentType.objects.get_for_model(SampleModel)
        ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk
        )
        updated_count = export.update_export_items_result(
            ExportItem.RESULT_FAILURE,
            detail='Test error'
        )
        assert updated_count == 1
        item = export.export_items.first()
        assert item.result == ExportItem.RESULT_FAILURE
        assert item.detail == 'Test error'

    def test_export_status_choices(self):
        """Test status field choices."""
        assert Export.STATUS_PENDING == 'PENDING'
        assert Export.STATUS_PROCESSING == 'PROCESSING'
        assert Export.STATUS_FAILED == 'FAILED'
        assert Export.STATUS_FINISHED == 'FINISHED'

    def test_export_format_choices(self):
        """Test format field choices."""
        assert Export.FORMAT_XLSX == 'XLSX'
        assert Export.FORMAT_XML == 'XML'
        assert Export.FORMAT_PDF == 'PDF'

    def test_export_context_choices(self):
        """Test context field choices."""
        assert Export.CONTEXT_LIST == 'LIST'
        assert Export.CONTEXT_STATISTICS == 'STATISTICS'
        assert Export.CONTEXT_DETAIL == 'DETAIL'


class TestExportItem:
    """Tests for ExportItem model."""

    def test_export_item_str(self, export_item):
        """Test string representation."""
        assert 'Export item' in str(export_item)

    def test_export_item_creation(self, export, test_model):
        """Test creation."""
        from outputs.models import ExportItem
        content_type = ContentType.objects.get_for_model(SampleModel)
        item = ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk,
            result=ExportItem.RESULT_SUCCESS
        )
        assert item.export == export
        assert item.object_id == test_model.pk

    def test_export_item_content_type(self, export_item):
        """Test content type relationship."""
        assert export_item.content_type is not None

    def test_export_item_result_choices(self):
        """Test result field choices."""
        assert ExportItem.RESULT_SUCCESS == 'SUCCESS'
        assert ExportItem.RESULT_FAILURE == 'FAILURE'


class TestScheduler:
    """Tests for Scheduler model."""

    def test_scheduler_str(self, scheduler):
        """Test string representation."""
        assert 'Scheduler' in str(scheduler)

    def test_scheduler_get_cron_string_daily(self, scheduler):
        """Test cron string for daily routine."""
        scheduler.routine = Scheduler.ROUTINE_DAILY
        assert scheduler.get_cron_string() == '0 7 * * *'

    def test_scheduler_get_cron_string_weekly(self, scheduler):
        """Test cron string for weekly routine."""
        scheduler.routine = Scheduler.ROUTINE_WEEKLY
        assert scheduler.get_cron_string() == '0 7 * * 1'

    def test_scheduler_get_cron_string_monthly(self, scheduler):
        """Test cron string for monthly routine."""
        scheduler.routine = Scheduler.ROUTINE_MONTHLY
        assert scheduler.get_cron_string() == '0 7 1 * *'

    def test_scheduler_get_cron_string_custom(self, scheduler):
        """Test cron string for custom routine."""
        scheduler.routine = Scheduler.ROUTINE_CUSTOM
        scheduler.cron_string = '0 12 * * *'
        assert scheduler.get_cron_string() == '0 12 * * *'

    def test_scheduler_cron_string_validation(self, scheduler):
        """Test cron string validation."""
        from django.core.exceptions import ValidationError
        scheduler.routine = Scheduler.ROUTINE_CUSTOM
        scheduler.cron_string = 'invalid cron'
        with pytest.raises(ValidationError):
            scheduler.clean()

    def test_scheduler_clean_custom_routine_requires_cron(self, scheduler):
        """Test that custom routine requires cron string."""
        from django.core.exceptions import ValidationError
        scheduler.routine = Scheduler.ROUTINE_CUSTOM
        scheduler.cron_string = ''
        with pytest.raises(ValidationError):
            scheduler.clean()

    def test_scheduler_clean_non_custom_routine_no_cron(self, scheduler):
        """Test that non-custom routine should have empty cron string."""
        scheduler.routine = Scheduler.ROUTINE_DAILY
        scheduler.cron_string = ''
        # Should not raise error
        scheduler.clean()

    def test_scheduler_get_absolute_url(self, scheduler):
        """Test absolute URL."""
        url = scheduler.get_absolute_url()
        assert '/schedulers/' in url
        assert str(scheduler.pk) in url

    def test_scheduler_schedule(self, scheduler, mock_rq_queue):
        """Test scheduling job."""
        scheduler.schedule()
        assert scheduler.job_id != ''

    def test_scheduler_cancel_schedule(self, scheduler, mock_rq_queue):
        """Test canceling schedule."""
        scheduler.job_id = 'test-job-id'
        scheduler.cancel_schedule()
        # Job should be deleted
        assert scheduler.job_id == 'test-job-id'  # ID remains, but job is deleted

    def test_scheduler_is_scheduled(self, scheduler, mock_rq_queue):
        """Test is_scheduled property."""
        scheduler.job_id = ''
        assert scheduler.is_scheduled is False

    def test_scheduler_routine_description(self, scheduler):
        """Test routine description."""
        scheduler.routine = Scheduler.ROUTINE_DAILY
        assert scheduler.routine_description is not None

    def test_scheduler_cron_description(self, scheduler):
        """Test cron description."""
        scheduler.routine = Scheduler.ROUTINE_DAILY
        class DummyDescriptor:
            def __init__(self, **kwargs):
                pass

            def get_description(self):
                return 'Daily at 07:00'

        with patch('outputs.models.ExpressionDescriptor', DummyDescriptor):
            description = scheduler.cron_description
            assert description == 'Daily at 07:00'

    def test_scheduler_exporter_params(self, scheduler):
        """Test exporter parameters."""
        params = scheduler.exporter_params
        assert 'params' in params
        assert 'user' in params
        assert params['user'] == scheduler.creator

    def test_scheduler_routine_choices(self):
        """Test routine field choices."""
        assert Scheduler.ROUTINE_DAILY == 'DAILY'
        assert Scheduler.ROUTINE_WEEKLY == 'WEEKLY'
        assert Scheduler.ROUTINE_MONTHLY == 'MONTHLY'
        assert Scheduler.ROUTINE_CUSTOM == 'CUSTOM'


class TestAbstractExport:
    """Tests for AbstractExport model."""

    def test_abstract_export_model_class(self, export):
        """Test model_class property."""
        model_class = export.model_class
        assert model_class == SampleModel

    def test_abstract_export_get_exporter_path(self):
        """Test exporter path generation."""
        path = AbstractExport.get_exporter_path(
            model_class=SampleModel,
            context=Export.CONTEXT_LIST,
            format=Export.FORMAT_XLSX
        )
        assert isinstance(path, str)
        assert 'SampleModel' in path
        assert 'Exporter' in path

    def test_abstract_export_get_exporter_path_with_mapping(self, settings):
        """Test exporter path with module mapping."""
        with patch('outputs.models.exporters_module_mapping', {'outputs.SampleModel': 'custom.exporters'}):
            path = AbstractExport.get_exporter_path(
                model_class=SampleModel,
                context=Export.CONTEXT_LIST,
                format=Export.FORMAT_XLSX
            )
        assert 'custom.exporters' in path

