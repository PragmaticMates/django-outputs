"""
Pytest configuration and fixtures for django-outputs tests.
"""
import os
import sys
# Disable GDAL for tests (django-select2 or django.contrib.gis may try to import it)
# Set this before any Django imports
os.environ.setdefault('GDAL_LIBRARY_PATH', '/fake/path')

# Provide a stub whistle.helpers.notify for signal imports
import types
if 'whistle' not in sys.modules:
    sys.modules['whistle'] = types.ModuleType('whistle')
if 'whistle.helpers' not in sys.modules:
    helpers_module = types.ModuleType('whistle.helpers')
    def _noop_notify(**kwargs):
        return None
    helpers_module.notify = _noop_notify
    sys.modules['whistle.helpers'] = helpers_module

# Mock GDAL before Django tries to import it
if 'django.contrib.gis.gdal' not in sys.modules:
    from unittest.mock import MagicMock
    gdal_mock = MagicMock()
    sys.modules['django.contrib.gis.gdal'] = gdal_mock
    sys.modules['django.contrib.gis'] = MagicMock(gdal=gdal_mock)

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from unittest.mock import Mock, patch
import fakeredis
from django.template.response import TemplateResponse

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

# Patch import_string to return MockExporter for test exporter paths
from unittest.mock import patch
from django.utils.module_loading import import_string as original_import_string

def mock_import_string(path):
    """Mock import_string to handle test exporter paths."""
    # If trying to import a test exporter path, return MockExporter
    if 'tests' in path and 'Exporter' in path:
        return MockExporter
    # Otherwise use original import_string
    return original_import_string(path)

# Patch import_string globally for tests
patch('django.utils.module_loading.import_string', side_effect=mock_import_string).start()
patch('outputs.models.import_string', side_effect=mock_import_string).start()


@pytest.fixture(autouse=True)
def skip_template_render(monkeypatch):
    """Avoid rendering templates to keep tests independent of HTML files."""
    def _render(self, *args, **kwargs):
        self._is_rendered = True
        self.content = b""
        return self
    monkeypatch.setattr(TemplateResponse, "render", _render)


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
def user_with_perms(user):
    """Create a test user with all outputs permissions."""
    from django.contrib.auth.models import Permission
    perms = Permission.objects.filter(content_type__app_label='outputs')
    user.user_permissions.set(perms)
    return user


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
    # Ensure a stable ContentType row exists even if registry isn't populated
    ContentType.objects.clear_cache()
    content_type, _ = ContentType.objects.get_or_create(
        app_label='outputs',
        model='samplemodel',
    )
    return content_type


@pytest.fixture
def test_model(db):
    """Create a test model instance."""
    return SampleModel.objects.create(
        name='Test Item',
        email='test@example.com',
        is_active=True
    )


@pytest.fixture
def export(db, user, content_type, exporter_class):
    """Create a test export."""
    # Set exporter_path to avoid import errors
    exporter_path = f'{exporter_class.__module__}.{exporter_class.__name__}'
    
    export = Export.objects.create(
        content_type=content_type,
        format=Export.FORMAT_XLSX,
        context=Export.CONTEXT_LIST,
        creator=user,
        total=10,
        status=Export.STATUS_PENDING,
        query_string='name=test',
        exporter_path=exporter_path
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
def scheduler(db, user, content_type, exporter_class):
    """Create a test scheduler."""
    # Set exporter_path to avoid import errors
    exporter_path = f'{exporter_class.__module__}.{exporter_class.__name__}'
    
    return Scheduler.objects.create(
        content_type=content_type,
        format=Scheduler.FORMAT_XLSX,
        context=Scheduler.CONTEXT_LIST,
        routine=Scheduler.ROUTINE_DAILY,
        creator=user,
        is_active=True,
        language='en',
        query_string='name=test',
        exporter_path=exporter_path
    )


# Global mock exporter class that can be imported
class MockExporter:
    def __init__(self, **kwargs):
        self.params = kwargs.get('params', {})
        self.user = kwargs.get('user')
        self.recipients = kwargs.get('recipients', [])
        self.selected_fields = kwargs.get('selected_fields', None)
        self.items = kwargs.get('items', None)
        self.output = None
        self.filename = 'test_export.xlsx'
        self.content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

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

@pytest.fixture
def exporter_class():
    """Mock exporter class."""
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


@pytest.fixture(autouse=True)
def create_test_model_table(db):
    """Create SampleModel table for tests."""
    from django.db import connection
    from django.contrib.contenttypes.models import ContentType
    from outputs.tests.models import SampleModel
    
    # Create the table if it doesn't exist
    with connection.schema_editor() as schema_editor:
        try:
            schema_editor.create_model(SampleModel)
        except Exception:
            # Table might already exist, ignore
            pass

    # Ensure ContentType exists for SampleModel
    ContentType.objects.get_for_model(SampleModel)
