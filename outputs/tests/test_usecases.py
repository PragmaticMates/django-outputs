"""
Tests for usecases module.
"""
import pytest
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.core.files.base import ContentFile
from unittest.mock import Mock, patch, MagicMock

from outputs.models import Export, ExportItem
from outputs.usecases import execute_export, export_items, mail_export, get_message
from outputs.tests.models import SampleModel


class TestExecuteExport:
    """Tests for execute_export function."""

    def test_execute_export_success(self, exporter_class, mock_storage, mock_email_backend):
        """Test successful export execution."""
        exporter = exporter_class(user=None, recipients=[])
        exporter.save_export = Mock(return_value=Mock(
            id=1,
            total=10,
            send_mail=Mock()
        ))
        
        execute_export(exporter, language='en')
        assert exporter.save_export.called
        assert exporter.save_export.return_value.send_mail.called

    def test_execute_export_failure(self, exporter_class):
        """Test export execution failure."""
        exporter = exporter_class(user=None, recipients=[])
        exporter.save_export = Mock(side_effect=Exception('Export failed'))
        
        with pytest.raises(Exception):
            execute_export(exporter, language='en')


class TestExportItems:
    """Tests for export_items function."""

    def test_export_items_success(self, export, test_model, exporter_class, mock_storage, mock_email_backend):
        """Test successful item export."""
        from outputs.models import ExportItem
        content_type = ContentType.objects.get_for_model(SampleModel)
        ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk
        )
        
        exporter = exporter_class(user=export.creator, recipients=export.recipients.all())
        exporter.export = Mock()
        exporter.get_filename = Mock(return_value='test.xlsx')
        exporter.get_output = Mock(return_value=b'test content')
        
        export_items(export, language='en', exporter=exporter)
        
        export.refresh_from_db()
        assert export.status == Export.STATUS_FINISHED
        assert ExportItem.objects.filter(export=export, result=ExportItem.RESULT_SUCCESS).exists()

    def test_export_items_failure(self, export, test_model, exporter_class):
        """Test export failure."""
        from outputs.models import ExportItem
        content_type = ContentType.objects.get_for_model(SampleModel)
        ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk
        )
        
        exporter = exporter_class(user=export.creator, recipients=export.recipients.all())
        exporter.export = Mock(side_effect=Exception('Export error'))
        exporter.get_filename = Mock(return_value='test.xlsx')
        
        with pytest.raises(Exception):
            export_items(export, language='en', exporter=exporter)
        
        export.refresh_from_db()
        assert export.status == Export.STATUS_FAILED
        assert ExportItem.objects.filter(export=export, result=ExportItem.RESULT_FAILURE).exists()

    def test_export_items_status_updates(self, export, test_model, exporter_class, mock_storage, mock_email_backend):
        """Test status updates during export."""
        from outputs.models import ExportItem
        content_type = ContentType.objects.get_for_model(SampleModel)
        ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk
        )
        
        exporter = exporter_class(user=export.creator, recipients=export.recipients.all())
        exporter.export = Mock()
        exporter.get_filename = Mock(return_value='test.xlsx')
        exporter.get_output = Mock(return_value=b'test content')
        
        # Check initial status
        assert export.status == Export.STATUS_PENDING
        
        export_items(export, language='en', exporter=exporter)
        
        export.refresh_from_db()
        assert export.status == Export.STATUS_FINISHED

    def test_export_items_export_item_updates(self, export, test_model, exporter_class, mock_storage, mock_email_backend):
        """Test ExportItem updates."""
        from outputs.models import ExportItem
        content_type = ContentType.objects.get_for_model(SampleModel)
        item = ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk
        )
        
        exporter = exporter_class(user=export.creator, recipients=export.recipients.all())
        exporter.export = Mock()
        exporter.get_filename = Mock(return_value='test.xlsx')
        exporter.get_output = Mock(return_value=b'test content')
        
        export_items(export, language='en', exporter=exporter)
        
        item.refresh_from_db()
        assert item.result == ExportItem.RESULT_SUCCESS

    def test_export_items_transaction(self, export, test_model, exporter_class):
        """Test transaction handling on failure."""
        from outputs.models import ExportItem
        content_type = ContentType.objects.get_for_model(SampleModel)
        ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk
        )
        
        exporter = exporter_class(user=export.creator, recipients=export.recipients.all())
        exporter.export = Mock(side_effect=Exception('Transaction error'))
        exporter.get_filename = Mock(return_value='test.xlsx')
        
        with pytest.raises(Exception):
            export_items(export, language='en', exporter=exporter)
        
        # Status should be updated even on failure
        export.refresh_from_db()
        assert export.status == Export.STATUS_FAILED


class TestMailExport:
    """Tests for mail_export function."""

    def test_mail_export_send_separately(self, export, exporter_class, mock_storage, mock_email_backend):
        """Test sending emails separately."""
        export.send_separately = True
        export.recipients.add(export.creator)
        
        exporter = exporter_class(user=export.creator, recipients=export.recipients.all())
        exporter.get_filename = Mock(return_value='test.xlsx')
        exporter.get_output = Mock(return_value=b'test content')
        exporter.get_message_body = Mock(return_value='Test body')
        
        mail_export(export, exporter=exporter)
        
        # Should send separate emails for each recipient
        assert len(mail.outbox) == export.recipients.count()

    def test_mail_export_send_together(self, export, exporter_class, mock_storage, mock_email_backend):
        """Test sending email together."""
        export.send_separately = False
        export.recipients.add(export.creator)
        
        exporter = exporter_class(user=export.creator, recipients=export.recipients.all())
        exporter.get_filename = Mock(return_value='test.xlsx')
        exporter.get_output = Mock(return_value=b'test content')
        exporter.get_message_body = Mock(return_value='Test body')
        
        mail_export(export, exporter=exporter)
        
        # Should send one email to all recipients
        assert len(mail.outbox) == 1
        assert len(mail.outbox[0].to) == export.recipients.count()

    def test_mail_export_save_as_file(self, export, exporter_class, mock_storage, mock_email_backend, settings):
        """Test saving as file."""
        settings.OUTPUTS_SAVE_AS_FILE = True
        export.send_separately = False
        
        exporter = exporter_class(user=export.creator, recipients=export.recipients.all())
        exporter.get_filename = Mock(return_value='test.xlsx')
        exporter.get_output = Mock(return_value=b'test content')
        exporter.get_message_body = Mock(return_value='Test body')
        
        mail_export(export, exporter=exporter)
        
        assert mock_storage.save.called

    def test_mail_export_without_save_as_file(self, export, exporter_class, mock_storage, mock_email_backend, settings):
        """Test without saving file."""
        settings.OUTPUTS_SAVE_AS_FILE = False
        export.send_separately = False
        
        exporter = exporter_class(user=export.creator, recipients=export.recipients.all())
        exporter.get_filename = Mock(return_value='test.xlsx')
        exporter.get_output = Mock(return_value=b'test content')
        exporter.get_message_body = Mock(return_value='Test body')
        
        mail_export(export, exporter=exporter)
        
        # File should be attached to email
        assert len(mail.outbox) == 1
        assert len(mail.outbox[0].attachments) > 0

    def test_mail_export_export_item_status(self, export, test_model, exporter_class, mock_storage, mock_email_backend):
        """Test export item status update."""
        from outputs.models import ExportItem
        content_type = ContentType.objects.get_for_model(SampleModel)
        item = ExportItem.objects.create(
            export=export,
            content_type=content_type,
            object_id=test_model.pk
        )
        
        exporter = exporter_class(user=export.creator, recipients=export.recipients.all())
        exporter.get_filename = Mock(return_value='test.xlsx')
        exporter.get_output = Mock(return_value=b'test content')
        exporter.get_message_body = Mock(return_value='Test body')
        
        mail_export(export, exporter=exporter)
        
        item.refresh_from_db()
        assert item.result == ExportItem.RESULT_SUCCESS
        export.refresh_from_db()
        assert export.status == Export.STATUS_FINISHED


class TestGetMessage:
    """Tests for get_message function."""

    def test_get_message_with_attachment(self, exporter_class):
        """Test message with attachment."""
        exporter = exporter_class(user=None, recipients=[])
        exporter.get_filename = Mock(return_value='test.xlsx')
        exporter.get_output = Mock(return_value=b'test content')
        exporter.get_message_body = Mock(return_value='Test body')
        exporter.content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        message = get_message(
            exporter,
            count=10,
            recipient_list=['test@example.com'],
            subject='Test Export'
        )
        
        assert message.subject == 'Test Export'
        assert len(message.attachments) > 0

    def test_get_message_with_file_url(self, exporter_class):
        """Test message with file URL."""
        exporter = exporter_class(user=None, recipients=[])
        exporter.get_message_body = Mock(return_value='Test body')
        
        message = get_message(
            exporter,
            count=10,
            recipient_list=['test@example.com'],
            subject='Test Export',
            file_url='/media/exports/test.xlsx'
        )
        
        assert message.subject == 'Test Export'
        # When file_url is provided, attachment should not be added
        assert len(message.attachments) == 0

    def test_get_message_subject(self, exporter_class):
        """Test message subject."""
        exporter = exporter_class(user=None, recipients=[])
        exporter.get_message_body = Mock(return_value='Test body')
        exporter.get_message_subject = Mock(return_value='Custom Subject')
        
        message = get_message(
            exporter,
            count=10,
            recipient_list=['test@example.com'],
            subject='Default Subject'
        )
        
        assert message.subject == 'Custom Subject'

    def test_get_message_body(self, exporter_class):
        """Test message body."""
        exporter = exporter_class(user=None, recipients=[])
        exporter.get_message_body = Mock(return_value='<html>Test body</html>')
        
        message = get_message(
            exporter,
            count=10,
            recipient_list=['test@example.com'],
            subject='Test Export'
        )
        
        assert '<html>Test body</html>' in message.body

