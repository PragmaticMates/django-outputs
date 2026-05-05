"""
Tests for jobs.
"""
import pytest
from unittest.mock import MagicMock, patch
from django.http import QueryDict

from outputs.models import Export
from outputs.jobs import (
    mail_export_by_id,
    execute_export,
)
from outputs.utils import (
    serialize_exporter_params,
    deserialize_exporter_params,
)
from outputs.tests.models import SampleModel


class TestSerializeDeserializeExporterParams:
    """Tests for serialize_exporter_params / deserialize_exporter_params."""

    def test_serialize_replaces_user_with_id(self, user):
        params = {'user': user, 'recipients': [], 'filename': 'out.xlsx'}
        result = serialize_exporter_params(params)

        assert 'user' not in result
        assert result['user_id'] == user.pk
        assert result['filename'] == 'out.xlsx'

    def test_serialize_replaces_recipients_with_ids(self, user, other_user):
        params = {'user': user, 'recipients': [user, other_user]}
        result = serialize_exporter_params(params)

        assert 'recipients' not in result
        assert set(result['recipient_ids']) == {user.pk, other_user.pk}

    def test_serialize_with_queryset_adds_ids_and_model(self, user):
        SampleModel.objects.create(name='A', email='a@example.com')
        SampleModel.objects.create(name='B', email='b@example.com')
        qs = SampleModel.objects.all()

        params = {'user': user, 'recipients': [], 'queryset': qs}
        result = serialize_exporter_params(params)

        assert 'queryset' not in result
        assert 'queryset_ids' in result
        assert 'queryset_model' in result
        assert set(result['queryset_ids']) == set(qs.values_list('pk', flat=True))
        assert result['queryset_model'] == 'outputs.samplemodel'

    def test_serialize_without_queryset_omits_keys(self, user):
        """queryset_ids / queryset_model must be absent — not None — when queryset not supplied."""
        params = {'user': user, 'recipients': []}
        result = serialize_exporter_params(params)

        assert 'queryset' not in result
        assert 'queryset_ids' not in result
        assert 'queryset_model' not in result

    def test_deserialize_round_trip_without_queryset(self, user, other_user):
        params = {
            'user': user,
            'recipients': [user, other_user],
            'filename': 'out.xlsx',
        }
        serialized = serialize_exporter_params(params)
        deserialized = deserialize_exporter_params(serialized)

        assert deserialized['user'] == user
        assert [u.pk for u in deserialized['recipients']] == [user.pk, other_user.pk]
        assert deserialized['filename'] == 'out.xlsx'
        assert 'queryset' not in deserialized

    def test_deserialize_round_trip_with_queryset(self, user):
        obj_a = SampleModel.objects.create(name='A', email='a@example.com')
        obj_b = SampleModel.objects.create(name='B', email='b@example.com')
        qs = SampleModel.objects.filter(pk__in=[obj_a.pk, obj_b.pk])

        params = {'user': user, 'recipients': [], 'queryset': qs}
        serialized = serialize_exporter_params(params)
        deserialized = deserialize_exporter_params(serialized)

        assert 'queryset' in deserialized
        assert set(deserialized['queryset'].values_list('pk', flat=True)) == {obj_a.pk, obj_b.pk}

    def test_deserialize_preserves_queryset_order(self, user):
        obj_a = SampleModel.objects.create(name='A', email='a@example.com')
        obj_b = SampleModel.objects.create(name='B', email='b@example.com')
        serialized = {
            'user_id': user.pk,
            'recipient_ids': [],
            'queryset_ids': [obj_b.pk, obj_a.pk],
            'queryset_model': 'outputs.samplemodel',
        }
        deserialized = deserialize_exporter_params(serialized)
        assert list(deserialized['queryset'].values_list('pk', flat=True)) == [obj_b.pk, obj_a.pk]

    def test_deserialize_queryset_absent_when_keys_missing(self, user):
        # A serialized dict that never had a queryset
        serialized = {'user_id': user.pk, 'recipient_ids': [], 'filename': 'x.xlsx'}
        deserialized = deserialize_exporter_params(serialized)

        assert 'queryset' not in deserialized
        assert 'queryset_ids' not in deserialized
        assert 'queryset_model' not in deserialized

    def test_serialize_none_user(self):
        params = {'user': None, 'recipients': []}
        result = serialize_exporter_params(params)
        assert result['user_id'] is None

    def test_deserialize_none_user_id(self):
        serialized = {'user_id': None, 'recipient_ids': []}
        deserialized = deserialize_exporter_params(serialized)
        assert deserialized['user'] is None

    def test_deserialize_noop_for_already_deserialized_payload(self, user, other_user):
        payload = {
            'user': user,
            'recipients': [other_user],
            'params': QueryDict('status=ok'),
            'filename': 'export.xlsx',
        }
        deserialized = deserialize_exporter_params(payload)
        assert deserialized == payload


class TestExecuteExport:
    """Tests for the execute_export background job."""

    def test_execute_export_calls_save_export_and_send_mail(self, user):
        """Full job: deserializes params, calls save_export and send_mail."""
        mock_export = MagicMock()
        mock_export.id = 1
        mock_export.total = 5
        mock_exporter = MagicMock()
        mock_exporter.save_export.return_value = mock_export

        mock_exporter_class = MagicMock(return_value=mock_exporter)

        serialized = serialize_exporter_params({'user': user, 'recipients': [user]})

        with patch('outputs.jobs.deserialize_exporter_params', wraps=deserialize_exporter_params):
            execute_export(mock_exporter_class, serialized, 'en')

        mock_exporter.save_export.assert_called_once()
        mock_export.send_mail.assert_called_once_with('en', None)

    def test_execute_export_reraises_on_failure(self, user):
        """Exceptions from save_export propagate out of the job."""
        mock_exporter = MagicMock()
        mock_exporter.save_export.side_effect = RuntimeError("boom")
        mock_exporter_class = MagicMock(return_value=mock_exporter)

        serialized = serialize_exporter_params({'user': user, 'recipients': []})

        with pytest.raises(RuntimeError, match="boom"):
            execute_export(mock_exporter_class, serialized, 'en')

    def test_execute_export_imports_exporter_class_from_path(self, user):
        mock_export = MagicMock()
        mock_export.id = 1
        mock_export.total = 3
        mock_exporter = MagicMock()
        mock_exporter.save_export.return_value = mock_export
        mock_exporter_class = MagicMock(return_value=mock_exporter)
        serialized = serialize_exporter_params({'user': user, 'recipients': [user], 'filename': 'x.xlsx'})

        with patch('outputs.jobs.import_string', return_value=mock_exporter_class) as mock_import:
            execute_export('outputs.tests.exporters.MockExporter', serialized, 'en')

        mock_import.assert_called_once_with('outputs.tests.exporters.MockExporter')
        mock_export.send_mail.assert_called_once_with('en', 'x.xlsx')


class TestMailExportById:
    """Tests for mail_export_by_id job."""

    def test_mail_export_by_id_success(self, export):
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

    def test_mail_export_by_id_failure(self, export):
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

    def test_mail_export_by_id_status_update(self, export):
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

    def test_mail_export_by_id_language(self, export):
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
