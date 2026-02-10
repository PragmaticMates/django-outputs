from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from outputs import settings as outputs_settings
from outputs.models import Export, Scheduler, ExportItem



def _get_all_exporter_subclasses(cls):
    """Return all subclasses of cls recursively."""
    return set(cls.__subclasses__()).union(
        s for c in cls.__subclasses__() for s in _get_all_exporter_subclasses(c)
    )


def get_exporter_path_choices():
    """Return choices of (path, label) for all ExporterMixin subclasses that do not end with 'Mixin'.

    The label uses the ExporterMixin.get_description() implementation, which is
    generic for all subclasses unless they override `description`.
    """
    from outputs.mixins import ExporterMixin

    choices = []

    # Sort exporters alphabetically by class name
    exporter_classes = sorted(
        _get_all_exporter_subclasses(ExporterMixin),
        key=lambda cls: cls.__name__,
    )

    for exporter_cls in exporter_classes:
        if exporter_cls.__name__.endswith('Mixin'):
            continue
        path = exporter_cls.get_path()
        if path in outputs_settings.EXCLUDE_EXPORTERS:
            continue
        label = exporter_cls.get_description() or path
        choices.append((path, label))

    return choices

class ExportedWithExporterListFilter(admin.SimpleListFilter):
    title = _('exported with exporter')
    parameter_name = 'exported_with_exporter'

    def lookups(self, request, model_admin):
        """
        Show all available exporter classes (children of ExporterMixin).
        """
        return get_exporter_path_choices()

    def queryset(self, request, queryset):
        """
        Filter exports that have been successfully finished using the selected exporter.
        """
        value = self.value()
        if not value:
            return queryset
        return queryset.filter(exporter_path=value)

@admin.register(Export)
class ExportAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    search_fields = ['creator__first_name', 'creator__last_name']
    list_select_related = ['creator', 'content_type']
    list_filter = ['status', 'output_type', 'format', 'context', 'content_type', ExportedWithExporterListFilter]
    list_display = ('id', 'content_type', 'output_type', 'format', 'context', 'exporter_path', 'status', 'creator', 'total', 'created')
    actions = ['send_mail']
    autocomplete_fields = ['creator', 'recipients']
    fields = [
        'status', 'total', 'url',
        ('content_type', 'format', 'context', 'output_type'),
        ('exporter_path', 'fields', 'query_string'),
        ('creator', 'recipients', 'emails', 'send_separately'),
        'created', 'modified'
    ]
    readonly_fields = ['total', 'created', 'modified']
    ordering = ('-created',)

    def send_mail(self, request, queryset):
        for obj in queryset.all():
            obj.send_mail(language=request.LANGUAGE_CODE)

    def view_on_site(self, obj):
        return obj.get_absolute_url()


@admin.register(ExportItem)
class ExportItemAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    ordering = ['-created']
    list_display = ['id', 'export_link', 'content_type_short', 'export_output_type', 'object_id', 'result', 'detail_short', 'created']
    list_filter = ['result', 'created', 'export__output_type']
    search_fields = ['export__id', 'object_id']
    list_select_related = ['export', 'content_type']
    readonly_fields = ['export', 'content_type', 'object_id', 'result', 'detail', 'created']
    fields = ['export', 'content_type', 'object_id', 'result', 'detail', 'created']
    autocomplete_fields = ['export']
    show_full_result_count = False  # Disable full count for better performance on large tables
    
    def export_link(self, obj):
        """Display export ID as a link to the export detail page."""
        if obj.export_id:
            from django.utils.html import format_html
            from django.urls import reverse
            url = reverse('admin:outputs_export_change', args=[obj.export_id])
            return format_html('<a href="{}">Export #{}</a>', url, obj.export_id)
        return '-'
    export_link.short_description = _('Export')
    export_link.admin_order_field = 'export_id'

    def export_output_type(self, obj):
        return obj.export.get_output_type_display() if obj.export else '-'
    export_output_type.short_description = _('Output Type')
    export_output_type.admin_order_field = 'export__output_type'
    
    def content_type_short(self, obj):
        """Display content type without calling model_class() which can be slow."""
        return obj.content_type.model if obj.content_type else '-'
    content_type_short.short_description = _('Content Type')
    content_type_short.admin_order_field = 'content_type'
    
    def detail_short(self, obj):
        """Display truncated detail to avoid rendering very long text fields in list view."""
        if obj.detail:
            return obj.detail[:100] + '...' if len(obj.detail) > 100 else obj.detail
        return '-'
    detail_short.short_description = _('Detail')


@admin.register(Scheduler)
class SchedulerAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    search_fields = ['creator__first_name', 'creator__last_name']
    list_select_related = ['creator', 'content_type']
    list_filter = ['routine', 'is_active', 'format', 'context', 'content_type']
    list_display = ('id', 'is_active', 'routine', 'cron_string', 'cron_description', 'content_type', 'format', 'creator', 'created')
    autocomplete_fields = ['creator', 'recipients']
