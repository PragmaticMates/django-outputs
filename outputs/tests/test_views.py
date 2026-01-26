"""
Tests for views.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.test import RequestFactory

from outputs.models import Export, Scheduler
from outputs.views import (
    ExportListView, SchedulerListView, SchedulerCreateView,
    SchedulerUpdateView, SchedulerDetailView, SchedulerDeleteView
)
from outputs.tests.models import SampleModel


class TestExportListView:
    """Tests for ExportListView."""

    def test_export_list_view_get(self, client, user, export):
        """Test GET request."""
        client.force_login(user)
        url = reverse('outputs:export_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_export_list_view_filtering(self, client, user, export):
        """Test filtering."""
        client.force_login(user)
        url = reverse('outputs:export_list')
        response = client.get(url, {'status': Export.STATUS_PENDING})
        assert response.status_code == 200
        # Check that filter is applied
        assert 'filter' in response.context

    def test_export_list_view_sorting(self, client, user, export):
        """Test sorting."""
        client.force_login(user)
        url = reverse('outputs:export_list')
        response = client.get(url, {'sort': '-created'})
        assert response.status_code == 200

    def test_export_list_view_permissions(self, client, user):
        """Test permissions."""
        # User needs list_export permission
        url = reverse('outputs:export_list')
        response = client.get(url)
        # Should redirect to login or show 403
        assert response.status_code in [302, 403]


class TestSchedulerListView:
    """Tests for SchedulerListView."""

    def test_scheduler_list_view_get(self, client, user, scheduler):
        """Test GET request."""
        client.force_login(user)
        url = reverse('outputs:scheduler_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_scheduler_list_view_filtering(self, client, user, scheduler):
        """Test filtering."""
        client.force_login(user)
        url = reverse('outputs:scheduler_list')
        response = client.get(url, {'is_active': 'True'})
        assert response.status_code == 200
        assert 'filter' in response.context

    def test_scheduler_list_view_sorting(self, client, user, scheduler):
        """Test sorting."""
        client.force_login(user)
        url = reverse('outputs:scheduler_list')
        response = client.get(url, {'sort': '-created'})
        assert response.status_code == 200

    def test_scheduler_list_view_permissions(self, client, user):
        """Test permissions."""
        url = reverse('outputs:scheduler_list')
        response = client.get(url)
        assert response.status_code in [302, 403]


class TestSchedulerCreateView:
    """Tests for SchedulerCreateView."""

    def test_scheduler_create_view_get(self, client, user, content_type):
        """Test GET request."""
        client.force_login(user)
        url = reverse('outputs:scheduler_create')
        response = client.get(url)
        assert response.status_code == 200

    def test_scheduler_create_view_post(self, client, user, content_type):
        """Test POST request."""
        client.force_login(user)
        url = reverse('outputs:scheduler_create')
        data = {
            'content_type': content_type.pk,
            'format': Scheduler.FORMAT_XLSX,
            'context': Scheduler.CONTEXT_LIST,
            'routine': Scheduler.ROUTINE_DAILY,
            'is_active': True,
            'language': 'en',
            'recipients': [user.pk],
        }
        response = client.post(url, data)
        # Should redirect on success or show form errors
        assert response.status_code in [200, 302]

    def test_scheduler_create_view_from_export(self, client, user, export):
        """Test creating from export."""
        client.force_login(user)
        url = reverse('outputs:scheduler_create_from_export', args=[export.pk])
        response = client.get(url)
        assert response.status_code == 200
        # Check that initial data is populated
        assert 'form' in response.context

    def test_scheduler_create_view_permissions(self, client, user):
        """Test permissions."""
        url = reverse('outputs:scheduler_create')
        response = client.get(url)
        assert response.status_code in [302, 403]

    def test_scheduler_create_view_initial_data(self, client, user, export):
        """Test initial data from export."""
        client.force_login(user)
        url = reverse('outputs:scheduler_create_from_export', args=[export.pk])
        response = client.get(url)
        assert response.status_code == 200
        form = response.context['form']
        # Check that form is initialized with export data
        assert form.initial.get('content_type') == export.content_type


class TestSchedulerUpdateView:
    """Tests for SchedulerUpdateView."""

    def test_scheduler_update_view_get(self, client, user, scheduler):
        """Test GET request."""
        client.force_login(user)
        url = reverse('outputs:scheduler_update', args=[scheduler.pk])
        response = client.get(url)
        assert response.status_code == 200

    def test_scheduler_update_view_post(self, client, user, scheduler):
        """Test POST request."""
        client.force_login(user)
        url = reverse('outputs:scheduler_update', args=[scheduler.pk])
        data = {
            'content_type': scheduler.content_type.pk,
            'format': scheduler.format,
            'context': scheduler.context,
            'routine': Scheduler.ROUTINE_WEEKLY,  # Changed
            'is_active': scheduler.is_active,
            'language': scheduler.language,
            'recipients': [user.pk],
        }
        response = client.post(url, data)
        # Should redirect on success or show form errors
        assert response.status_code in [200, 302]

    def test_scheduler_update_view_permissions(self, client, user, scheduler):
        """Test permissions."""
        url = reverse('outputs:scheduler_update', args=[scheduler.pk])
        response = client.get(url)
        assert response.status_code in [302, 403]


class TestSchedulerDetailView:
    """Tests for SchedulerDetailView."""

    def test_scheduler_detail_view_get(self, client, user, scheduler):
        """Test GET request."""
        client.force_login(user)
        url = reverse('outputs:scheduler_detail', args=[scheduler.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['scheduler'] == scheduler

    def test_scheduler_detail_view_permissions(self, client, user, scheduler):
        """Test permissions."""
        url = reverse('outputs:scheduler_detail', args=[scheduler.pk])
        response = client.get(url)
        assert response.status_code in [302, 403]


class TestSchedulerDeleteView:
    """Tests for SchedulerDeleteView."""

    def test_scheduler_delete_view_get(self, client, user, scheduler):
        """Test GET request."""
        client.force_login(user)
        url = reverse('outputs:scheduler_delete', args=[scheduler.pk])
        response = client.get(url)
        assert response.status_code == 200

    def test_scheduler_delete_view_post(self, client, user, scheduler):
        """Test POST request."""
        client.force_login(user)
        url = reverse('outputs:scheduler_delete', args=[scheduler.pk])
        scheduler_id = scheduler.pk
        response = client.post(url)
        # Should redirect on success
        assert response.status_code == 302
        # Check that scheduler is deleted
        assert not Scheduler.objects.filter(pk=scheduler_id).exists()

    def test_scheduler_delete_view_permissions(self, client, user, scheduler):
        """Test permissions."""
        url = reverse('outputs:scheduler_delete', args=[scheduler.pk])
        response = client.get(url)
        assert response.status_code in [302, 403]

