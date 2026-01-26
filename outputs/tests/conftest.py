"""
Pytest configuration and fixtures for django-outputs tests.
"""
import pytest
import json
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage
from django.db import models
from unittest.mock import Mock, patch, MagicMock
import fakeredis

# Patch ArrayField to work with SQLite for testing
# This allows tests to use SQLite while models use PostgreSQL ArrayField
class SQLiteArrayField(models.TextField):
    """ArrayField compatibility for SQLite using JSON storage."""
    
    def __init__(self, base_field=None, **kwargs):
        self.base_field = base_field
        super().__init__(**kwargs)
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def to_python(self, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []
        return value or []
    
    def get_prep_value(self, value):
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            return json.dumps(value)
        return value
    
    def get_db_prep_value(self, value, connection, prepared=False):
        return self.get_prep_value(value)

# Patch ArrayField to use SQLite-compatible version for tests
# This must happen before models are imported
import django.contrib.postgres.fields
django.contrib.postgres.fields.ArrayField = SQLiteArrayField

# Patch get_task_decorator if not available in pragmatic version
# This must happen before jobs.py is imported
try:
    from pragmatic.utils import get_task_decorator
except ImportError:
    # Create a mock decorator if not available
    def get_task_decorator(queue_name):
        def decorator(func):
            return func
        return decorator
    # Patch it in pragmatic.utils
    import pragmatic.utils
    pragmatic.utils.get_task_decorator = get_task_decorator

from outputs.models import Export, ExportItem, Scheduler
from outputs.tests.models import SampleModel


@pytest.fixture
def user(db):
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def other_user(db):
    """Create another test user."""
    User = get_user_model()
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='testpass123',
        first_name='Other',
        last_name='User'
    )


@pytest.fixture
def superuser(db):
    """Create a superuser."""
    User = get_user_model()
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def content_type(db):
    """Create a ContentType for SampleModel."""
    return ContentType.objects.get_for_model(SampleModel)


@pytest.fixture
def test_model(db):
    """Create a test model instance."""
    return SampleModel.objects.create(
        name='Test Item',
        email='test@example.com',
        is_active=True
    )


@pytest.fixture
def export(db, user, content_type):
    """Create a test export."""
    export = Export.objects.create(
        content_type=content_type,
        format=Export.FORMAT_XLSX,
        context=Export.CONTEXT_LIST,
        creator=user,
        total=10,
        status=Export.STATUS_PENDING,
        query_string='name=test'
    )
    export.recipients.add(user)
    return export


@pytest.fixture
def export_item(db, export, content_type, test_model):
    """Create a test export item."""
    return ExportItem.objects.create(
        export=export,
        content_type=content_type,
        object_id=test_model.pk,
        result=ExportItem.RESULT_SUCCESS
    )


@pytest.fixture
def scheduler(db, user, content_type):
    """Create a test scheduler."""
    return Scheduler.objects.create(
        content_type=content_type,
        format=Scheduler.FORMAT_XLSX,
        context=Scheduler.CONTEXT_LIST,
        routine=Scheduler.ROUTINE_DAILY,
        creator=user,
        is_active=True,
        language='en',
        query_string='name=test'
    )


@pytest.fixture
def exporter_class():
    """Mock exporter class."""
    class MockExporter:
        def __init__(self, **kwargs):
            self.params = kwargs.get('params', {})
            self.user = kwargs.get('user')
            self.recipients = kwargs.get('recipients', [])
            self.selected_fields = kwargs.get('selected_fields', None)
            self.items = kwargs.get('items', None)
            self.output = None
            self.filename = 'test_export.xlsx'

        def get_filename(self):
            return self.filename

        def get_output(self):
            return b'test export content'

        def get_message_body(self, count, file_url=None):
            return f'Export contains {count} items'

        def get_message_subject(self):
            return None

        def export(self):
            pass

        def get_queryset(self):
            from outputs.tests.models import SampleModel
            return SampleModel.objects.all()

        @classmethod
        def get_path(cls):
            return 'outputs.tests.test_exporter.MockExporter'

        @classmethod
        def get_app_and_model(cls):
            return ('outputs', 'testmodel')

        export_format = Export.FORMAT_XLSX
        export_context = Export.CONTEXT_LIST

    return MockExporter


@pytest.fixture
def mock_storage(monkeypatch):
    """Mock storage backend."""
    mock_storage_backend = Mock()
    mock_storage_backend.save.return_value = 'exports/test_export.xlsx'
    mock_storage_backend.url.return_value = '/media/exports/test_export.xlsx'
    
    monkeypatch.setattr('outputs.usecases.default_storage', mock_storage_backend)
    return mock_storage_backend


@pytest.fixture
def mock_rq_queue(monkeypatch):
    """Mock RQ queue."""
    fake_redis = fakeredis.FakeStrictRedis()
    
    def get_queue(name='default'):
        queue = Mock()
        queue.connection = fake_redis
        return queue
    
    def get_scheduler(name='default'):
        scheduler = Mock()
        scheduler.get_jobs.return_value = []
        scheduler.enqueue_in = Mock()
        scheduler.cron = Mock(return_value=Mock(id='test-job-id'))
        return scheduler
    
    monkeypatch.setattr('django_rq.get_queue', get_queue)
    monkeypatch.setattr('django_rq.get_scheduler', get_scheduler)
    
    return {'queue': get_queue(), 'scheduler': get_scheduler()}


@pytest.fixture
def mock_email_backend(settings):
    """Use locmem email backend for testing."""
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    return settings


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests."""
    pass
