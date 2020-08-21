from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.utils.translation import ugettext_lazy as _
from pragmatic.mixins import LoginPermissionRequiredMixin, DisplayListViewMixin, SortingListViewMixin, DeleteObjectMixin
from outputs.filters import ExportFilter, SchedulerFilter
from outputs.forms import SchedulerForm
from outputs.models import Export, Scheduler


class ExportListView(LoginPermissionRequiredMixin, DisplayListViewMixin, SortingListViewMixin, ListView):
    model = Export
    filter_class = ExportFilter
    permission_required = 'outputs.list_export'
    displays = ['table']
    paginate_values = [10, 50, 100]
    paginate_by_display = {'table': paginate_values}
    sorting_options = {'-created': _('Newest'), 'created': _('Oldest'), 'creator': _('Creator'), 'total': _('Total items')}

    def dispatch(self, request, *args, **kwargs):
        self.filter = self.filter_class(self.request.GET, queryset=self.get_whole_queryset())
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.sort_queryset(self.filter.qs)

    def get_whole_queryset(self):
        return self.model.objects.all()\
            .select_related('creator', 'content_type')\
            .prefetch_related('recipients')

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data.update({'filter': self.filter})
        return context_data


class SchedulerListView(LoginPermissionRequiredMixin, DisplayListViewMixin, SortingListViewMixin, ListView):
    model = Scheduler
    filter_class = SchedulerFilter
    permission_required = 'outputs.list_scheduler'
    displays = ['table']
    paginate_values = [10, 50, 100]
    paginate_by_display = {'table': paginate_values}
    sorting_options = {'-created': _('Newest'), 'created': _('Oldest'), 'creator': _('Creator')}

    def dispatch(self, request, *args, **kwargs):
        self.filter = self.filter_class(self.request.GET, queryset=self.get_whole_queryset())
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.sort_queryset(self.filter.qs)

    def get_whole_queryset(self):
        return self.model.objects.all() \
            .select_related('creator', 'content_type') \
            .prefetch_related('recipients')

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data.update({'filter': self.filter})
        return context_data


class SchedulerCreateView(LoginPermissionRequiredMixin, CreateView):
    model = Scheduler
    form_class = SchedulerForm
    permission_required = 'outputs.add_scheduler'

    def dispatch(self, request, *args, **kwargs):
        export_pk = kwargs.get('export_pk', None)
        self.export = get_object_or_404(Export, pk=export_pk) if export_pk else None
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()

        initial.update({
            'language': self.request.LANGUAGE_CODE
        })

        if self.export:
            initial.update({
                'content_type': self.export.content_type,
                'fields': self.export.fields,
                'format': self.export.format,
                'context': self.export.context,
                'query_string': self.export.query_string,
                'recipients': self.export.recipients.all()
            })

        return initial

    def form_valid(self, form):
        messages.success(self.request, _('Scheduler successfully created'))
        scheduler = form.save(commit=False)
        scheduler.creator = self.request.user
        scheduler.save()
        return super().form_valid(form)


class SchedulerUpdateView(LoginPermissionRequiredMixin, UpdateView):
    model = Scheduler
    form_class = SchedulerForm
    permission_required = 'outputs.change_scheduler'

    def form_valid(self, form):
        messages.success(self.request, _('Scheduler successfully updated'))
        return super().form_valid(form)


class SchedulerDetailView(LoginPermissionRequiredMixin, DetailView):
    model = Scheduler
    permission_required = 'outputs.view_scheduler'


class SchedulerDeleteView(LoginPermissionRequiredMixin, DeleteObjectMixin, DeleteView):
    model = Scheduler
    success_url = reverse_lazy('outputs:scheduler_list')
    permission_required = 'outputs.delete_scheduler'
