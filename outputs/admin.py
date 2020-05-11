from django.contrib import admin

from outputs.models import Export, Scheduler


@admin.register(Export)
class ExportAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    search_fields = ['creator__first_name', 'creator__last_name']
    list_select_related = ['creator', 'content_type']
    list_filter = ['format', 'context', 'content_type']
    list_display = ('id', 'content_type', 'format', 'creator', 'total', 'created')
    actions = ['send_mail']

    def send_mail(self, request, queryset):
        for obj in queryset.all():
            obj.send_mail(language=request.LANGUAGE_CODE)


@admin.register(Scheduler)
class SchedulerAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    search_fields = ['creator__first_name', 'creator__last_name']
    list_select_related = ['creator', 'content_type']
    list_filter = ['routine', 'is_active', 'format', 'context', 'content_type']
    list_display = ('id', 'routine', 'is_active', 'content_type', 'format', 'creator', 'created')
