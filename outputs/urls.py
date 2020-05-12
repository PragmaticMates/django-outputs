from django.urls import path
from django.utils.translation import pgettext_lazy

from outputs.views import ExportListView, SchedulerListView, SchedulerCreateView, SchedulerUpdateView, SchedulerDetailView, SchedulerDeleteView

app_name = 'outputs'

urlpatterns = [
    path(pgettext_lazy('url', 'exports/'), ExportListView.as_view(), name='export_list'),
    path(pgettext_lazy("url", 'schedulers/<int:pk>/'), SchedulerDetailView.as_view(), name='scheduler_detail'),
    path(pgettext_lazy("url", 'schedulers/<int:pk>/update/'), SchedulerUpdateView.as_view(), name='scheduler_update'),
    path(pgettext_lazy("url", 'schedulers/<int:pk>/delete/'), SchedulerDeleteView.as_view(), name='scheduler_delete'),
    path(pgettext_lazy("url", 'schedulers/create/from-export/<int:export_pk>/'), SchedulerCreateView.as_view(), name='scheduler_create_from_export'),
    path(pgettext_lazy("url", 'schedulers/create/'), SchedulerCreateView.as_view(), name='scheduler_create'),
    path(pgettext_lazy('url', 'schedulers/'), SchedulerListView.as_view(), name='scheduler_list'),
]
