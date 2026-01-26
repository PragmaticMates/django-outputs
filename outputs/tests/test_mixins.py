"""
Tests for mixins.
"""
import pytest
from unittest.mock import Mock, patch

from outputs.mixins import (
    ExportFieldsPermissionsMixin, ConfirmExportMixin, SelectExportMixin,
    FilterExporterMixin, ExporterMixin, ExcelExporterMixin
)
from outputs.models import Export
from outputs.tests.models import SampleModel


class TestExportFieldsPermissionsMixin:
    """Tests for ExportFieldsPermissionsMixin."""

    def test_load_export_fields_permissions_string(self):
        """Test loading from string."""
        mixin = ExportFieldsPermissionsMixin()
        permissions = '{"exporter.path": ["field1", "field2"]}'
        result = mixin.load_export_fields_permissions(permissions)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)

    def test_load_export_fields_permissions_list(self):
        """Test loading from list."""
        mixin = ExportFieldsPermissionsMixin()
        permissions = ['{"exporter.path": ["field1"]}', '{"exporter.path": ["field2"]}']
        result = mixin.load_export_fields_permissions(permissions)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_load_export_fields_permissions_dict(self):
        """Test loading from dict."""
        mixin = ExportFieldsPermissionsMixin()
        permissions = {"exporter.path": ["field1", "field2"]}
        result = mixin.load_export_fields_permissions(permissions)
        assert isinstance(result, list)
        assert isinstance(result[0], dict)

    def test_combine_export_fields_permissions(self):
        """Test combining permissions."""
        mixin = ExportFieldsPermissionsMixin()
        permissions = [
            {"exporter1": ["field1", "field2"]},
            {"exporter1": ["field3"], "exporter2": ["field4"]}
        ]
        result = mixin.combine_export_fields_permissions(permissions)
        assert "exporter1" in result
        assert "exporter2" in result
        assert "field1" in result["exporter1"]
        assert "field3" in result["exporter1"]

    def test_substract_export_fields_permissions(self):
        """Test subtracting permissions."""
        mixin = ExportFieldsPermissionsMixin()
        first = {"exporter1": ["field1", "field2", "field3"]}
        second = {"exporter1": ["field2"]}
        result = mixin.substract_export_fields_permissions(first, second)
        assert "exporter1" in result
        assert "field1" in result["exporter1"]
        assert "field2" not in result["exporter1"]

    def test_substract_export_fields_permissions_all_removed(self):
        """Test subtracting when all fields are removed."""
        mixin = ExportFieldsPermissionsMixin()
        first = {"exporter1": ["field1", "field2"]}
        second = {"exporter1": ["field1", "field2"]}
        result = mixin.substract_export_fields_permissions(first, second)
        assert "exporter1" not in result


class TestConfirmExportMixin:
    """Tests for ConfirmExportMixin."""

    def test_confirm_export_mixin_get_initial(self):
        """Test initial data."""
        mixin = ConfirmExportMixin()
        mixin.request = Mock()
        mixin.request.user = Mock()
        mixin.exporter_class = Mock()
        mixin.exporter_class.filename = 'test.xlsx'
        
        initial = mixin.get_initial()
        assert 'recipients' in initial
        assert 'filename' in initial

    def test_confirm_export_mixin_get_exporter(self):
        """Test exporter creation."""
        mixin = ConfirmExportMixin()
        mixin.request = Mock()
        mixin.request.user = Mock()
        mixin.exporter_class = Mock()
        mixin.exporter_params = {'user': mixin.request.user}
        
        exporter = mixin.get_exporter()
        assert exporter is not None

    def test_confirm_export_mixin_get_objects_count(self):
        """Test object count."""
        mixin = ConfirmExportMixin()
        mixin.get_exporter = Mock(return_value=Mock(
            get_queryset=Mock(return_value=Mock(count=Mock(return_value=10)))
        ))
        
        count = mixin.get_objects_count()
        assert count == 10

    def test_confirm_export_mixin_export(self):
        """Test export execution."""
        mixin = ConfirmExportMixin()
        mixin.get_exporter = Mock(return_value=Mock())
        
        with patch('outputs.mixins.execute_export') as mock_execute:
            mixin.export()
            assert mock_execute.called

    def test_confirm_export_mixin_form_valid(self):
        """Test form validation."""
        mixin = ConfirmExportMixin()
        mixin.request = Mock()
        mixin.export = Mock()
        mixin.get_success_url = Mock(return_value='/success/')
        
        form = Mock()
        form.cleaned_data = {
            'recipients': [Mock()],
            'filename': 'test.xlsx'
        }
        
        with patch('outputs.mixins.super') as mock_super:
            mock_super.return_value.form_valid.return_value = Mock()
            result = mixin.form_valid(form)
            assert mixin.export.called


class TestSelectExportMixin:
    """Tests for SelectExportMixin."""

    def test_select_export_mixin_get_permitted_fields(self):
        """Test permitted fields."""
        mixin = SelectExportMixin()
        mixin.request = Mock()
        mixin.request.user = Mock()
        mixin.request.user.is_active = True
        mixin.request.user.is_superuser = True
        mixin.request.user.export_fields_permissions = None
        mixin.request.user.groups = Mock()
        mixin.request.user.groups.exclude.return_value.values_list.return_value = []
        mixin.exporter_class = Mock()
        mixin.exporter_class.get_path = Mock(return_value='exporter.path')
        
        fields = mixin.get_permitted_fields()
        # Superuser should get all fields (True)
        assert fields is True or isinstance(fields, list)

    def test_select_export_mixin_get_form_kwargs(self):
        """Test form kwargs."""
        mixin = SelectExportMixin()
        mixin.request = Mock()
        mixin.request.user = Mock()
        mixin.request.user.is_active = True
        mixin.request.user.is_superuser = False
        mixin.exporter_class = Mock()
        mixin.exporter_class.selectable_fields = Mock(return_value={'group1': [('field1', 'Field 1')]})
        
        kwargs = mixin.get_form_kwargs()
        assert 'selectable_fields' in kwargs
        assert 'permitted_fields' in kwargs


class TestFilterExporterMixin:
    """Tests for FilterExporterMixin."""

    def test_filter_exporter_mixin_get_filter(self):
        """Test filter creation."""
        mixin = FilterExporterMixin(params={}, queryset=SampleModel.objects.all())
        mixin.filter_class = Mock()
        mixin.get_whole_queryset = Mock(return_value=SampleModel.objects.all())
        
        filter_obj = mixin.get_filter()
        assert filter_obj is not None

    def test_filter_exporter_mixin_get_queryset(self):
        """Test queryset filtering."""
        mixin = FilterExporterMixin(params={}, queryset=SampleModel.objects.all())
        mixin.filter = Mock()
        mixin.filter.qs = SampleModel.objects.all()
        mixin.items = None
        
        qs = mixin.get_queryset()
        assert qs is not None

    def test_filter_exporter_mixin_get_queryset_with_items(self):
        """Test queryset filtering with items."""
        mixin = FilterExporterMixin(params={}, queryset=SampleModel.objects.all())
        mixin.filter = Mock()
        mixin.filter.queryset = SampleModel.objects.all()
        mixin.items = [1, 2, 3]
        
        qs = mixin.get_queryset()
        assert qs is not None

    def test_filter_exporter_mixin_get_message_body(self):
        """Test message body."""
        mixin = FilterExporterMixin(params={}, queryset=SampleModel.objects.all())
        mixin.filter = Mock()
        
        body = mixin.get_message_body(count=10)
        assert isinstance(body, str)


class TestExporterMixin:
    """Tests for ExporterMixin."""

    def test_exporter_mixin_get_path(self):
        """Test exporter path."""
        class TestExporter(ExporterMixin):
            pass
        
        path = TestExporter.get_path()
        assert isinstance(path, str)
        assert 'TestExporter' in path

    def test_exporter_mixin_get_description(self):
        """Test description."""
        class TestExporter(ExporterMixin):
            description = 'Test description'
        
        desc = TestExporter.get_description()
        assert desc == 'Test description'

    def test_exporter_mixin_get_filename(self):
        """Test filename."""
        exporter = ExporterMixin(user=None, recipients=[])
        exporter.filename = 'test.xlsx'
        
        filename = exporter.get_filename()
        assert filename == 'test.xlsx'

    def test_exporter_mixin_get_filename_raises_error(self):
        """Test filename raises error when not set."""
        exporter = ExporterMixin(user=None, recipients=[])
        exporter.filename = None
        
        with pytest.raises(ValueError):
            exporter.get_filename()

    def test_exporter_mixin_get_output(self):
        """Test output retrieval."""
        exporter = ExporterMixin(user=None, recipients=[])
        exporter.output.write(b'test content')
        
        output = exporter.get_output()
        assert output == b'test content'

    def test_exporter_mixin_export_to_response(self):
        """Test export to response."""
        exporter = ExporterMixin(user=None, recipients=[])
        exporter.filename = 'test.xlsx'
        exporter.content_type = 'application/octet-stream'
        exporter.export = Mock()
        exporter.get_output = Mock(return_value=b'test content')
        
        response = exporter.export_to_response()
        assert response.status_code == 200
        assert b'test content' in response.content

    def test_exporter_mixin_save_export(self, user):
        """Test saving export."""
        exporter = ExporterMixin(user=user, recipients=[user])
        exporter.queryset = SampleModel.objects.all()
        exporter.export_format = Export.FORMAT_XLSX
        exporter.export_context = Export.CONTEXT_LIST
        exporter.params = {}
        exporter.selected_fields = None
        
        # Create a test model instance
        test_model = SampleModel.objects.create(name='Test', email='test@example.com')
        
        export = exporter.save_export()
        assert export is not None
        assert export.creator == user
        assert export.total == 1

    def test_exporter_mixin_save_export_with_items(self, user):
        """Test saving export with items."""
        exporter = ExporterMixin(user=user, recipients=[user])
        exporter.queryset = SampleModel.objects.all()
        exporter.export_format = Export.FORMAT_XLSX
        exporter.export_context = Export.CONTEXT_LIST
        exporter.params = {}
        exporter.selected_fields = ['name', 'email']
        
        # Create test model instances
        SampleModel.objects.create(name='Test1', email='test1@example.com')
        SampleModel.objects.create(name='Test2', email='test2@example.com')
        
        export = exporter.save_export()
        assert export is not None
        assert export.total == 2
        # Check that ExportItems were created
        assert export.export_items.count() == 2


class TestExcelExporterMixin:
    """Tests for ExcelExporterMixin."""

    def test_excel_exporter_mixin_write_row(self):
        """Test writing row."""
        with patch('outputs.mixins.xlsxwriter') as mock_xlsx:
            mock_workbook = Mock()
            mock_worksheet = Mock()
            mock_workbook.add_worksheet.return_value = mock_worksheet
            mock_xlsx.Workbook.return_value = mock_workbook
            
            class TestExcelExporter(ExcelExporterMixin):
                def get_queryset(self):
                    return SampleModel.objects.none()
                
                def get_worksheet_title(self, index=0):
                    return 'Test'
            
            exporter = TestExcelExporter(user=None, recipients=[])
            field = ('name', 'Name', 20)
            obj = SampleModel(name='Test', email='test@example.com')
            
            exporter.write_row(mock_worksheet, 0, 0, obj, field)
            assert mock_worksheet.write.called

    def test_excel_exporter_mixin_write_header(self):
        """Test writing header."""
        with patch('outputs.mixins.xlsxwriter') as mock_xlsx:
            mock_workbook = Mock()
            mock_worksheet = Mock()
            mock_workbook.add_worksheet.return_value = mock_worksheet
            mock_xlsx.Workbook.return_value = mock_workbook
            
            class TestExcelExporter(ExcelExporterMixin):
                def get_queryset(self):
                    return SampleModel.objects.none()
                
                def get_worksheet_title(self, index=0):
                    return 'Test'
                
                @staticmethod
                def selectable_fields():
                    return {'group1': [('name', 'Name', 20)]}
            
            exporter = TestExcelExporter(user=None, recipients=[])
            fields = [('name', 'Name', 20)]
            exporter.write_header(mock_worksheet, fields, [])
            assert mock_worksheet.write.called

    def test_excel_exporter_mixin_get_selected_fields(self):
        """Test selected fields."""
        with patch('outputs.mixins.xlsxwriter') as mock_xlsx:
            mock_workbook = Mock()
            mock_xlsx.Workbook.return_value = mock_workbook
            
            class TestExcelExporter(ExcelExporterMixin):
                def get_queryset(self):
                    return SampleModel.objects.all()
                
                def get_worksheet_title(self, index=0):
                    return 'Test'
                
                @staticmethod
                def selectable_fields():
                    return {'group1': [('name', 'Name', 20), ('email', 'Email', 30)]}
            
            exporter = TestExcelExporter(user=None, recipients=[])
            exporter.selected_fields = ['name']
            
            # Create test objects
            SampleModel.objects.create(name='Test', email='test@example.com')
            
            fields, iterative = exporter.get_selected_fields(exporter.get_queryset())
            assert len(fields) == 1
            assert fields[0][0] == 'name'

    def test_excel_exporter_mixin_get_paginator(self):
        """Test pagination."""
        with patch('outputs.mixins.xlsxwriter') as mock_xlsx:
            mock_workbook = Mock()
            mock_xlsx.Workbook.return_value = mock_workbook
            
            class TestExcelExporter(ExcelExporterMixin):
                def get_queryset(self):
                    return SampleModel.objects.all()
                
                def get_worksheet_title(self, index=0):
                    return 'Test'
            
            exporter = TestExcelExporter(user=None, recipients=[])
            
            # Create many test objects
            for i in range(10):
                SampleModel.objects.create(name=f'Test{i}', email=f'test{i}@example.com')
            
            with patch('outputs.mixins.settings') as mock_settings:
                mock_settings.NUMBER_OF_THREADS = 4
                paginator = exporter.get_paginator(exporter.get_queryset())
                # Should return paginator when count > NUMBER_OF_THREADS
                assert paginator is not None

