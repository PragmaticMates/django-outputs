import inspect

from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.validators import EMPTY_VALUES
from django.db import models
from django.http import QueryDict
from django.template import Context, Template
from django.template.defaultfilters import title
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _
from gm2m import GM2MField
from pytz import timezone
from rq.exceptions import NoSuchJobError
from rq.job import Job

from outputs import jobs
from outputs.cron import schedule_export
from outputs.querysets import ExportQuerySet, SchedulerQuerySet

from pragmatic.templatetags.pragmatic_tags import filtered_values


exporters_module_mapping = settings.OUTPUTS_EXPORTERS_MODULE_MAPPING
related_models = settings.OUTPUTS_RELATED_MODELS


class AbstractExport(models.Model):
    FORMAT_XLSX = 'XLSX'
    FORMAT_XML_MRP = 'XML_MRP'
    FORMAT_PDF = 'PDF'
    FORMATS = [
        (FORMAT_XLSX, 'XLSX'),
        (FORMAT_XML_MRP, 'XML MRP'),
        (FORMAT_PDF, 'PDF'),
    ]

    CONTEXT_LIST = 'LIST'
    CONTEXT_STATISTICS = 'STATISTICS'
    CONTEXT_DETAIL = 'DETAIL'
    CONTEXTS = [
        (CONTEXT_LIST, _('list')),
        (CONTEXT_STATISTICS, _('statistics')),
        (CONTEXT_DETAIL, _('detail'))
    ]

    content_type = models.ForeignKey(ContentType, verbose_name=_('content type'), on_delete=models.CASCADE)
    format = models.CharField(_('format'), choices=FORMATS, max_length=7)
    context = models.CharField(_('context'), choices=CONTEXTS, max_length=10)
    fields = ArrayField(verbose_name=_('fields'), base_field=models.CharField(max_length=40), blank=True, default=list)
    query_string = models.TextField(_('query string'), blank=True, default='')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('creator'), on_delete=models.PROTECT, related_name="%(class)s_where_creator",
                                blank=True, null=True, default=None)
    recipients = models.ManyToManyField(get_user_model(), verbose_name=_('recipients'), related_name="%(class)s_where_recipient", blank=True)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    modified = models.DateTimeField(_('modified'), auto_now=True)
    send_separately = models.BooleanField(_('send separately'), default=False)

    class Meta:
        abstract = True

    @property
    def model_class(self):
        return self.content_type.model_class()

    @staticmethod
    def get_exporter_class(model_class, context, format):
        exports_module = exporters_module_mapping.get(model_class._meta.label, None)

        if isinstance(exports_module, dict):
            exports_module = exports_module.get(context, None)

        if not exports_module:
            models_module = model_class.__module__
            app_module = models_module.rsplit('.', maxsplit=1)[0]
            exports_module = f'{app_module}.exporters'

        exporter_class_name = model_class.__name__
        format = title(format)
        format = format.replace('_', '')
        context = title(context)
        exporter_class_name = '{}{}{}Exporter'.format(exporter_class_name, format, context)
        exporter_path = f'{exports_module}.{exporter_class_name}'
        return import_string(exporter_path)

    @property
    def exporter_class(self):
        return AbstractExport.get_exporter_class(self.model_class, self.context, self.format)

    @property
    def exporter(self):
        constructor = self.exporter_class.__init__
        signature = inspect.signature(constructor)
        arguments = signature.parameters.keys()

        params = self.exporter_params.copy()

        for key in list(params.keys()):
            if key not in arguments and 'kwargs' not in arguments:
                params.pop(key)

        return self.exporter_class(**params)

    @property
    def exporter_params(self):
        return {
            'params': self.params,
            'user': self.creator,
            'recipients': self.recipients.all(),
            'selected_fields': self.fields,
            'send_separately': self.send_separately
        }

    @property
    def params(self):
        return QueryDict(self.query_string)

    @property
    def recipients_emails(self):
        return list(self.recipients.values_list('email', flat=True))

    def get_params_display(self):
        result = ''

        filter = self.exporter.filter

        filter_values = filtered_values(filter, self.params)

        for param, field in filter_values.items():
            label = field['label']
            value = field['value']

            value = Template("{{ value }}").render(Context({'value': value}))  # workaround for datetime ranges
            result = f'{result}{label}: {value}\n'

        return result

    def get_fields_labels(self):
        field_labels = []
        exporter = self.exporter

        try:
            selectable_fields = exporter.selectable_fields()
        except AttributeError:
            selectable_fields = None

        try:
            for set in exporter.selectable_iterative_sets().values():
                selectable_fields.update(set)
        except AttributeError:
            pass

        selectable_fields_with_labels = {}
        if selectable_fields:
            for field_group in selectable_fields.values():
                for field in field_group:
                    selectable_fields_with_labels[field[0]] = field[1]

        for field in self.fields:
            field_labels.append(selectable_fields_with_labels.get(field, field))

        return field_labels


class Export(AbstractExport):
    STATUS_PENDING = 'PENDING'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_FAILED = 'FAILED'
    STATUS_FINISHED = 'FINISHED'
    STATUSES = [
        (STATUS_PENDING, _('pending')),
        (STATUS_PROCESSING, _('processing')),
        (STATUS_FAILED, _('failed')),
        (STATUS_FINISHED, _('finished'))
    ]
    status = models.CharField(_('status'), choices=STATUSES, max_length=10, default=STATUS_PENDING)
    items = GM2MField(*related_models, related_name='exports_where_item')
    total = models.PositiveIntegerField(_('total items'), default=0)
    emails = ArrayField(
        verbose_name=_('emails'),
        base_field=models.EmailField(),
        default=list,
    )
    objects = ExportQuerySet.as_manager()
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _('export')
        verbose_name_plural = _('exports')
        ordering = ('created',)
        default_permissions = settings.DEFAULT_PERMISSIONS

    def __str__(self):
        model = self.content_type.model_class()
        name = model._meta.verbose_name_plural if model else self.content_type.model
        return '{} #{} ({})'.format(_('Export'), self.pk, name)

    def _get_base_url(self):
        app_label = self.get_app_label()
        url = reverse(f'{app_label}:{self.content_type.model}_list')
        return url

    def get_items_url(self):
        return f'{self._get_base_url()}?export={self.pk}'

    def get_absolute_url(self):
        return f'{self._get_base_url()}?{self.query_string}'

    def get_app_label(self):
        if self.context in [self.CONTEXT_LIST, self.CONTEXT_DETAIL]:
            app_label = self.content_type.app_label

            if app_label == 'invoicing':  # TODO: refactor
                app_label = 'billing'
            elif app_label == 'exports':
                app_label = 'outputs'

        else:
            module = exporters_module_mapping[self.model_class._meta.label][self.context]
            app_label = module.split('.')[-2]

        return app_label

    def send_mail(self, language, filename=None):
        export_class_name = f'{self.__class__.__module__}.{self.__class__.__name__}'
        jobs.mail_export.delay(self.pk, export_class_name, language, filename)

    @property
    def object_list(self):
        ids = list(self.items.all().values_list('gm2m_pk', flat=True))
        # ids = list(map(int, ids))
        model = self.content_type.model_class()
        return model.objects.filter(id__in=ids)

    @property
    def exporter_params(self):
        return {
            'params': self.params,
            'items': self.object_list,  # this is required as we want to send identically same export (not currently available filtered data)
            'user': self.creator,
            'recipients': self.recipients.all(),
            'selected_fields': self.fields
        }


class Scheduler(AbstractExport):
    ROUTINE_OFTEN = 'OFTEN'                 # for debug purposes
    ROUTINE_DAILY = 'DAILY'                 # every morning at 8:00
    ROUTINE_WEEKLY = 'WEEKLY'               # every monday at 8:00
    ROUTINE_MONTHLY = 'MONTHLY'             # at 1st of current month TODO: reports will be for the previous month
    ROUTINES = [
        # (ROUTINE_OFTEN, _('often')),
        (ROUTINE_DAILY, _('daily')),
        (ROUTINE_WEEKLY, _('weekly')),
        (ROUTINE_MONTHLY, _('monthly'))
    ]

    ROUTINE_DESCRIPTIONS = {
        # ROUTINE_OFTEN: _('every minute'),  # 6 UTC
        ROUTINE_DAILY: _('at 8:00'),  # 6 UTC
        ROUTINE_WEEKLY: _('on Monday'),
        ROUTINE_MONTHLY: _('on the first day'),
    }

    routine = models.CharField(_('routine'), choices=ROUTINES, max_length=7)
    is_active = models.BooleanField(_('active'), default=True)
    executions = ArrayField(verbose_name=_('executions'), base_field=models.DateTimeField(), blank=True, default=list)
    job_id = models.CharField('job ID', max_length=36, blank=True)
    language = models.CharField(_('language'), choices=settings.LANGUAGES, max_length=2, db_index=True, default='en')
    # TODO: filename
    objects = SchedulerQuerySet.as_manager()
    history = AuditlogHistoryField()

    class Meta:
        verbose_name = _('scheduler')
        verbose_name_plural = _('schedulers')
        ordering = ('created',)
        default_permissions = settings.DEFAULT_PERMISSIONS

    def __str__(self):
        return '{} #{} ({} - {})'.format(_('Scheduler'), self.pk, self.content_type.model_class()._meta.verbose_name_plural, self.get_routine_display())

    def get_absolute_url(self):
        return reverse('outputs:scheduler_detail', args=(self.pk,))

    @property
    def job(self):
        if self.job_id in EMPTY_VALUES:
            return None

        queue = django_rq.get_queue('cron')

        try:
            return Job.fetch(self.job_id, connection=queue.connection)
        except NoSuchJobError:
            return None

    @property
    def schedule_time(self):
        if not self.is_scheduled:
            return None

        # get all scheduled jobs
        scheduler = django_rq.get_scheduler('cron')
        jobs = scheduler.get_jobs(with_times=True)

        # get scheduler job by its ID
        # job, scheduled_at = list(filter(lambda x: x[0].id == self.job_id, jobs))[0]  # this is slower because it iterates whole array
        job, scheduled_at = next(x for x in jobs if x[0].id == self.job_id)            # returns first match

        # read time from scheduler
        scheduled_at = scheduled_at.replace(tzinfo=timezone('UTC'))
        scheduled_at = scheduled_at.astimezone(timezone(settings.TIME_ZONE))
        return scheduled_at

    @property
    def is_scheduled(self):
        return self.job is not None

    @property
    def routine_description(self):
        return self.ROUTINE_DESCRIPTIONS.get(self.routine)

    def cancel_schedule(self):
        if self.is_scheduled:
            self.job.delete()

    def schedule(self):
        # cancel previous cron job
        self.cancel_schedule()

        if self.is_active:
            # schedule cronjob for active scheduler and save its ID
            scheduler = django_rq.get_scheduler('cron')

            # schedule export as cron job
            scheduler_class_name = f'{self.__class__.__module__}.{self.__class__.__name__}'
            job = scheduler.cron(
                self.cron,
                func=schedule_export,
                args=(self.pk, scheduler_class_name),
                timeout=settings.RQ_QUEUES['cron']['DEFAULT_TIMEOUT']
            )
            
            self.job_id = job.id
        else:
            # inactive scheduler doesn't have job ID
            self.job_id = ''

        self.save(update_fields=['job_id'])

    @property
    def cron(self):
        # ┌───────────── minute (0 - 59)
        # │ ┌───────────── hour (0 - 23)
        # │ │ ┌───────────── day of the month (1 - 31)
        # │ │ │ ┌───────────── month (1 - 12)
        # │ │ │ │ ┌───────────── day of the week (0 - 6) (Sunday to Saturday;
        # │ │ │ │ │                                   7 is also Sunday on some systems)
        # │ │ │ │ │
        # │ │ │ │ │
        # * * * * *

        # All times are in UTC timezone

        # if self.routine == self.ROUTINE_OFTEN:  # for debug purposes
        #     return "* * * * *"

        if self.routine == self.ROUTINE_DAILY:
            return "0 5 * * *"

        if self.routine == self.ROUTINE_WEEKLY:
            return "0 5 * * 1"

        if self.routine == self.ROUTINE_MONTHLY:
            return "0 5 1 * *"

        raise NotImplementedError()


auditlog.register(Export, exclude_fields=['modified', 'creator'])
auditlog.register(Scheduler, exclude_fields=['modified', 'creator', 'executions', 'job_id'])

from .signals import *
