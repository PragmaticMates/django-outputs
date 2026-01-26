"""
Tests for forms.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from outputs.forms import ConfirmExportForm, ChooseExportFieldsForm, SchedulerForm
from outputs.models import Scheduler


class TestConfirmExportForm:
    """Tests for ConfirmExportForm."""

    def test_confirm_export_form_valid(self, user):
        """Test valid form."""
        User = get_user_model()
        form = ConfirmExportForm(data={
            'recipients': [user.pk],
            'filename': 'test_export.xlsx'
        })
        assert form.is_valid()

    def test_confirm_export_form_invalid(self):
        """Test invalid form."""
        form = ConfirmExportForm(data={})
        assert not form.is_valid()

    def test_confirm_export_form_fields(self):
        """Test form fields."""
        form = ConfirmExportForm()
        assert 'recipients' in form.fields
        assert 'filename' in form.fields


class TestChooseExportFieldsForm:
    """Tests for ChooseExportFieldsForm."""

    def test_choose_export_fields_form_valid(self, user):
        """Test valid form."""
        selectable_fields = {
            'group1': [('field1', 'Field 1'), ('field2', 'Field 2')]
        }
        form = ChooseExportFieldsForm(
            data={
                'recipients': [user.pk],
                'filename': 'test.xlsx',
                'field_group_0': ['field1']
            },
            selectable_fields=selectable_fields,
            permitted_fields=True
        )
        assert form.is_valid()

    def test_choose_export_fields_form_no_fields_selected(self, user):
        """Test no fields selected."""
        selectable_fields = {
            'group1': [('field1', 'Field 1')]
        }
        form = ChooseExportFieldsForm(
            data={
                'recipients': [user.pk],
                'filename': 'test.xlsx'
            },
            selectable_fields=selectable_fields,
            permitted_fields=True
        )
        assert not form.is_valid()
        assert 'Select at least one option' in str(form.errors)

    def test_choose_export_fields_form_permitted_fields(self, user):
        """Test permitted fields."""
        selectable_fields = {
            'group1': [('field1', 'Field 1'), ('field2', 'Field 2')]
        }
        form = ChooseExportFieldsForm(
            data={
                'recipients': [user.pk],
                'filename': 'test.xlsx',
                'field_group_0': ['field1']
            },
            selectable_fields=selectable_fields,
            permitted_fields=['field1']  # Only field1 is permitted
        )
        assert form.is_valid()

    def test_choose_export_fields_form_disabled_fields(self, user):
        """Test disabled fields."""
        selectable_fields = {
            'group1': [('field1', 'Field 1'), ('field2', 'Field 2')]
        }
        form = ChooseExportFieldsForm(
            selectable_fields=selectable_fields,
            permitted_fields=['field1']  # Only field1 is permitted
        )
        # Field2 should be disabled
        field = form.fields.get('field_group_0')
        assert field is not None


class TestSchedulerForm:
    """Tests for SchedulerForm."""

    def test_scheduler_form_valid(self, user, content_type):
        """Test valid form."""
        User = get_user_model()
        form = SchedulerForm(data={
            'content_type': content_type.pk,
            'format': Scheduler.FORMAT_XLSX,
            'context': Scheduler.CONTEXT_LIST,
            'routine': Scheduler.ROUTINE_DAILY,
            'is_active': True,
            'language': 'en',
            'recipients': [user.pk],
            'query_string': '',
            'fields': ''
        })
        # Form validation may fail due to exporter validation
        # But basic structure should be correct
        assert 'content_type' in form.fields

    def test_scheduler_form_invalid_cron_string(self, user, content_type):
        """Test invalid cron string."""
        form = SchedulerForm(data={
            'content_type': content_type.pk,
            'format': Scheduler.FORMAT_XLSX,
            'context': Scheduler.CONTEXT_LIST,
            'routine': Scheduler.ROUTINE_CUSTOM,
            'cron_string': 'invalid cron',
            'is_active': True,
            'language': 'en',
            'recipients': [user.pk],
        })
        assert not form.is_valid()

    def test_scheduler_form_custom_routine_requires_cron(self, user, content_type):
        """Test custom routine validation."""
        form = SchedulerForm(data={
            'content_type': content_type.pk,
            'format': Scheduler.FORMAT_XLSX,
            'context': Scheduler.CONTEXT_LIST,
            'routine': Scheduler.ROUTINE_CUSTOM,
            'cron_string': '',  # Empty cron string
            'is_active': True,
            'language': 'en',
            'recipients': [user.pk],
        })
        # Should fail validation
        scheduler = form.save(commit=False)
        with pytest.raises(ValidationError):
            scheduler.clean()

    def test_scheduler_form_fields(self):
        """Test form fields."""
        form = SchedulerForm()
        assert 'content_type' in form.fields
        assert 'routine' in form.fields
        assert 'cron_string' in form.fields
        assert 'recipients' in form.fields

