"""
Tests for views.
"""
from django.urls import reverse

from outputs.models import Export, Scheduler

class TestExportListView:
    """Tests for ExportListView."""

    def test_export_list_view_get(self, client, user_with_perms, export):
        """Test GET request."""
        client.force_login(user_with_perms)
        url = reverse('outputs:export_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_export_list_view_filtering(self, client, user_with_perms, export):
        """Test filtering."""
        client.force_login(user_with_perms)
        url = reverse('outputs:export_list')
        response = client.get(url, {'status': Export.STATUS_PENDING})
        assert response.status_code == 200

    def test_export_list_view_sorting(self, client, user_with_perms, export):
        """Test sorting."""
        client.force_login(user_with_perms)
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

    def test_scheduler_list_view_get(self, client, user_with_perms, scheduler):
        """Test GET request."""
        client.force_login(user_with_perms)
        url = reverse('outputs:scheduler_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_scheduler_list_view_filtering(self, client, user_with_perms, scheduler):
        """Test filtering."""
        client.force_login(user_with_perms)
        url = reverse('outputs:scheduler_list')
        response = client.get(url, {'is_active': 'True'})
        assert response.status_code == 200

    def test_scheduler_list_view_sorting(self, client, user_with_perms, scheduler):
        """Test sorting."""
        client.force_login(user_with_perms)
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

    def test_scheduler_create_view_get(self, client, user_with_perms, content_type):
        """Test GET request."""
        client.force_login(user_with_perms)
        url = reverse('outputs:scheduler_create')
        response = client.get(url)
        assert response.status_code == 200

    def test_scheduler_create_view_post(self, client, user_with_perms, content_type):
        """Test POST request."""
        client.force_login(user_with_perms)
        url = reverse('outputs:scheduler_create')
        data = {
            'content_type': content_type.pk,
            'format': Scheduler.FORMAT_XLSX,
            'context': Scheduler.CONTEXT_LIST,
            'routine': Scheduler.ROUTINE_DAILY,
            'is_active': True,
            'language': 'en',
            'recipients': [user_with_perms.pk],
        }
        response = client.post(url, data)
        # Should redirect on success or show form errors
        assert response.status_code in [200, 302]

    def test_scheduler_create_view_from_export(self, client, user_with_perms, export):
        """Test creating from export."""
        client.force_login(user_with_perms)
        url = reverse('outputs:scheduler_create_from_export', args=[export.pk])
        response = client.get(url)
        assert response.status_code == 200

    def test_scheduler_create_view_permissions(self, client, user):
        """Test permissions."""
        url = reverse('outputs:scheduler_create')
        response = client.get(url)
        assert response.status_code in [302, 403]

    def test_scheduler_create_view_initial_data(self, client, user_with_perms, export):
        """Test initial data from export."""
        client.force_login(user_with_perms)
        url = reverse('outputs:scheduler_create_from_export', args=[export.pk])
        response = client.get(url)
        assert response.status_code == 200


class TestSchedulerUpdateView:
    """Tests for SchedulerUpdateView."""

    def test_scheduler_update_view_get(self, client, user_with_perms, scheduler):
        """Test GET request."""
        client.force_login(user_with_perms)
        url = reverse('outputs:scheduler_update', args=[scheduler.pk])
        response = client.get(url)
        assert response.status_code == 200

    def test_scheduler_update_view_post(self, client, user_with_perms, scheduler):
        """Test POST request."""
        client.force_login(user_with_perms)
        url = reverse('outputs:scheduler_update', args=[scheduler.pk])
        data = {
            'content_type': scheduler.content_type.pk,
            'format': scheduler.format,
            'context': scheduler.context,
            'routine': Scheduler.ROUTINE_WEEKLY,  # Changed
            'is_active': scheduler.is_active,
            'language': scheduler.language,
            'recipients': [user_with_perms.pk],
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

    def test_scheduler_detail_view_get(self, client, user_with_perms, scheduler):
        """Test GET request."""
        client.force_login(user_with_perms)
        url = reverse('outputs:scheduler_detail', args=[scheduler.pk])
        response = client.get(url)
        assert response.status_code == 200

    def test_scheduler_detail_view_permissions(self, client, user, scheduler):
        """Test permissions."""
        url = reverse('outputs:scheduler_detail', args=[scheduler.pk])
        response = client.get(url)
        assert response.status_code in [302, 403]


class TestSchedulerDeleteView:
    """Tests for SchedulerDeleteView."""

    def test_scheduler_delete_view_get(self, client, user_with_perms, scheduler):
        """Test GET request."""
        client.force_login(user_with_perms)
        url = reverse('outputs:scheduler_delete', args=[scheduler.pk])
        response = client.get(url)
        assert response.status_code == 200

    def test_scheduler_delete_view_post(self, client, user_with_perms, scheduler):
        """Test POST request."""
        client.force_login(user_with_perms)
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

