"""
Tests for widgets.
"""
import pytest
import json
from unittest.mock import Mock, patch

from outputs.widgets import (
    ExportFieldsPermissionsSelectMultipleWidget,
    CheckboxSelectMultipleWithDisabled
)


class TestExportFieldsPermissionsSelectMultipleWidget:
    """Tests for ExportFieldsPermissionsSelectMultipleWidget."""

    def test_widget_render(self):
        """Test widget rendering."""
        widget = ExportFieldsPermissionsSelectMultipleWidget()
        
        with patch.object(widget, 'get_table') as mock_table:
            mock_table.return_value = []
            result = widget.render('test_field', None)
            assert isinstance(result, str)

    def test_widget_decompress(self):
        """Test value decompression."""
        widget = ExportFieldsPermissionsSelectMultipleWidget()
        
        with patch.object(widget, 'get_all_exportable_fields') as mock_fields:
            mock_fields.return_value = {
                'exporter.path': {'group1': [('field1', 'Field 1')]}
            }
            
            value = json.dumps({'exporter.path': ['field1']})
            result = widget.decompress(value)
            assert isinstance(result, set)
            assert 'exporter.path/field1' in result

    def test_widget_format_output(self):
        """Test output formatting."""
        widget = ExportFieldsPermissionsSelectMultipleWidget()
        
        value = ['exporter.path/field1', 'exporter.path/field2']
        result = widget.format_output(value, compress=True)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert 'exporter.path' in parsed
        assert 'field1' in parsed['exporter.path']

    def test_widget_format_output_no_compress(self):
        """Test output formatting without compression."""
        widget = ExportFieldsPermissionsSelectMultipleWidget()
        
        value = ['exporter.path/field1']
        result = widget.format_output(value, compress=False)
        assert isinstance(result, dict)
        assert 'exporter.path' in result


class TestCheckboxSelectMultipleWithDisabled:
    """Tests for CheckboxSelectMultipleWithDisabled widget."""

    def test_widget_disabled_option(self):
        """Test disabled option rendering."""
        widget = CheckboxSelectMultipleWithDisabled()
        
        option = widget.create_option(
            name='test',
            value='value1',
            label={'label': 'Test Label', 'disabled': True},
            selected=False,
            index=0
        )
        
        assert option['attrs'].get('disabled') == 'disabled'

    def test_widget_enabled_option(self):
        """Test enabled option rendering."""
        widget = CheckboxSelectMultipleWithDisabled()
        
        option = widget.create_option(
            name='test',
            value='value1',
            label='Test Label',
            selected=False,
            index=0
        )
        
        assert 'disabled' not in option['attrs'] or option['attrs'].get('disabled') != 'disabled'

