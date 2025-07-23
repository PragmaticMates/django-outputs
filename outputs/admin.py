from django.contrib import admin

from outputs.models import Export, Scheduler


@admin.register(Export)
class ExportAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    search_fields = ['creator__first_name', 'creator__last_name']
    list_select_related = ['creator', 'content_type']
    list_filter = ['status', 'format', 'context', 'content_type']
    list_display = ('id', 'content_type', 'format', 'context', 'status', 'creator', 'total', 'created')
    actions = ['send_mail']
    autocomplete_fields = ['creator', 'recipients']
    fields = [
        'status', 'total', 'url',
        ('content_type', 'format', 'context'),
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


@admin.register(Scheduler)
class SchedulerAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    search_fields = ['creator__first_name', 'creator__last_name']
    list_select_related = ['creator', 'content_type']
    list_filter = ['routine', 'is_active', 'format', 'context', 'content_type']
    list_display = ('id', 'is_active', 'routine', 'cron_string', 'cron_description', 'content_type', 'format', 'creator', 'created')
    autocomplete_fields = ['creator', 'recipients']
