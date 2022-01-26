import datetime
import io
import json
import operator

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, QuerySet
from django.http import HttpResponse
from django.template import loader
from django.utils import translation
from django.utils.timezone import localtime
from django.utils.translation import ugettext_lazy as _

from pragmatic.templatetags.pragmatic_tags import filtered_values
from outputs import jobs
from outputs.forms import ChooseExportFieldsForm, ConfirmExportForm
from outputs.models import Export


class ExportFieldsPermissionsMixin(object):
    def load_export_fields_permissions(self, permissions):
        """
        Take single export_fields_permissions or their list or tuple and returns list of their json loaded versions, e.g. dictionaries
        """
        if isinstance(permissions, str):
            permissions = (permissions,)
        elif not isinstance(permissions, (list, tuple, QuerySet)):
            raise TypeError()

        loaded_permissions = []
        for permission in permissions:
            if not isinstance(permission, dict):
                permission = json.loads(permission)

            if isinstance(permission, str):
                permission = json.loads(permission)

            if not isinstance(permission, dict):
                raise TypeError()

            loaded_permissions.append(permission)

        return loaded_permissions

    def combine_export_fields_permissions(self, permissions):
        """
        Take list or tuple of json laoded export_fields_permissions and returns their union, e.g. combine them into a single dictionary
        """
        if not isinstance(permissions, (list, tuple, QuerySet)):
            raise TypeError()
        elif len(permissions) == 1:
            return permissions[0]

        result = {}
        for permission in permissions:
            for exporter, fields in permission.items():
                if exporter not in result:
                    result[exporter] = set()

                result[exporter].update(set(fields))

        for key, value in result.items():
            result[key] = list(value)

        return result

    def substract_export_fields_permissions(self, first, second):
        """
        Take two json laoded export_fields_permissions, first and second and returns first - second
        """
        if not isinstance(first, dict) or not isinstance(second, dict):
            raise TypeError()

        result = dict(first)
        for exporter, fields in first.items():
            if exporter in second:
                first_set = set(fields)
                second_set = set(second[exporter])
                if first_set <= second_set:
                    del result[exporter]
                else:
                    result[exporter] = list(set(fields) - set(second[exporter]))

        return result


class ConfirmExportMixin(object):
    template_name = 'outputs/export_confirmation.html'
    back_url = None
    form_class = ConfirmExportForm

    def get_success_url(self):
        return self.get_back_url()

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        initial = super().get_initial()
        initial['recipients'] = self.request.user
        initial['filename'] = self.exporter_class.filename

        return initial

    @property
    def exporter_params(self):
        return {
            'user': self.request.user,
            'recipients': getattr(self, 'recipients', []),
            'params': self.get_params(),
            'filename': getattr(self, 'filename', None)
        }

    def get_params(self):
        params = self.request.GET.copy()

        try:
            params.pop('back_url')
        except KeyError:
            pass

        return params

    def get_back_url(self):
        url = self.request.GET.get('back_url', self.back_url)
        if not url:
            raise ValueError()
        return url

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['back_url'] = self.get_back_url()
        context_data['objects_count'] = self.get_objects_count()
        return context_data

    def get_exporter(self):
        return self.exporter_class(**self.exporter_params)

    def export(self):
        jobs.execute_export.delay(self.exporter_class, self.exporter_params, language=translation.get_language())

    def get_objects_count(self):
        return self.get_exporter().get_queryset().count()

    def form_valid(self, form):
        self.recipients = form.cleaned_data.pop('recipients')
        self.filename = form.cleaned_data.pop('filename')
        self.export()
        messages.info(self.request, _('Your request is being processed. It can take few minutes. The result will be sent to your email.'))
        return super().form_valid(form)


class SelectExportMixin(ConfirmExportMixin, ExportFieldsPermissionsMixin):
    template_name = 'outputs/export_selection.html'
    form_class = ChooseExportFieldsForm
    limit = None
    selected_fields = []

    @property
    def exporter_params(self):
        return {
            'user': self.request.user,
            'recipients': getattr(self, 'recipients', []),
            'params': self.get_params(),
            'selected_fields': self.selected_fields,
            'filename': getattr(self, 'filename', None)
        }

    def form_valid(self, form):
        self.selected_fields = []
        for label, fields in form.cleaned_data.items():
            self.selected_fields += fields
        return super().form_valid(form)

    def get_permitted_fields(self):
        if not hasattr(self.exporter_class, 'selectable_fields'):
            return []

        permissions = []
        if self.request.user.export_fields_permissions:
            permissions.append(self.request.user.export_fields_permissions)

        permissions.extend(
            self.request.user.groups
                .exclude(metadata__export_fields_permissions__isnull=True)
                .values_list('metadata__export_fields_permissions', flat=True)
        )

        permissions = self.combine_export_fields_permissions(
            self.load_export_fields_permissions(permissions)
        )

        if not permissions:
            return []

        app_name, model_name = self.exporter_class.queryset.model._meta.label.split('.')
        export_format = self.exporter_class.export_format
        export_format = export_format.capitalize()
        exporter_key = '.'.join([app_name, model_name, export_format])

        try:
            return permissions[exporter_key]
        except KeyError:
            return []

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        if hasattr(self.exporter_class, 'selectable_fields'):
            selectable_fields = self.exporter_class.selectable_fields()
        else:
            selectable_fields = None

        try:
            for set in self.exporter_class.selectable_iterative_sets().values():
                selectable_fields.update(set)
        except AttributeError:
            pass

        kwargs['selectable_fields'] = selectable_fields
        kwargs['permitted_fields'] = True if self.request.user.is_active and self.request.user.is_superuser else self.get_permitted_fields()
        return kwargs


class FilterExporterMixin(object):
    filter_class = None
    queryset = None
    model = None

    def __init__(self, params, **kwargs):
        self.params = params
        self.items = kwargs.pop('items', None)
        super().__init__(**kwargs)

        # create filter
        self.filter = self.get_filter()

    @classmethod
    def get_model(cls):
        return cls.queryset.model if cls.queryset is not None else cls.model

    def get_filter(self):
        return self.filter_class(self.params, queryset=self.get_whole_queryset(self.params))

    def get_whole_queryset(self, params):
        proxy = params.get('proxy', None)

        if proxy:
            self.queryset = self.queryset.proxy(proxy)

        return self.queryset

    def get_queryset(self):
        items = getattr(self, 'items')

        if items:
            return self.filter.queryset.filter(pk__in=items)

        return self.filter.qs

    def get_message_body(self, count):
        template = loader.get_template('outputs/export_message_body.html')
        fv = filtered_values(self.filter, self.params)
        return template.render({'count': count, 'filtered_values': fv})


class ExporterMixin(object):
    content_type = 'application/force-download'
    filename = None
    export_format = None
    export_context = None
    send_separately = False

    def __init__(self, user, recipients, **kwargs):
        self.filename = kwargs.pop('filename', self.filename)
        self.send_separately = kwargs.pop('send_separately', self.send_separately)
        self.user = user
        self.recipients = recipients

        # initialize stream
        self.output = io.BytesIO()

    def get_filename(self):
        if not self.filename:
            raise ValueError()

        # remove accents
        self.filename = self.filename.encode('ascii', 'ignore')
        self.filename = self.filename.decode('utf-8')

        return self.filename

    def export(self):
        raise NotImplementedError()

    def write_data(self, output):
        raise NotImplementedError()

    def get_output(self):
        self.output.seek(0)
        return self.output.read()

    def export_to_response(self):
        self.export()

        # construct response
        response = HttpResponse(
            self.get_output(),
            content_type=self.content_type,
        )
        response['Content-Disposition'] = "attachment; filename={}".format(
            self.get_filename()
        )

        return response

    def get_message_body(self, count):
        raise NotImplementedError()

    def get_message_subject(self):
        return None

    def save_export(self):
        items = self.get_queryset().all()
        model = self.queryset.model
        params = getattr(self, 'params', {})

        fields = getattr(self, 'selected_fields', None)

        if fields is None:  # exporting all fields by default
            if hasattr(self, 'selectable_fields'):
                fields = []
                for label, fieldset in self.selectable_fields().items():
                    for field_definition in fieldset:
                        fields.append(field_definition[0])  # TODO: use map()

        # track export
        export = Export.objects.create(
            content_type=ContentType.objects.get_for_model(model, for_concrete_model=False),
            format=self.export_format,
            context=self.export_context,
            fields=fields,
            creator=self.user,
            query_string=params.urlencode(),
            total=items.count(),
            emails=[recipient.email for recipient in self.recipients]
        )
        export.recipients.add(*list(self.recipients))

        try:
            export.items.add(*list(items))
        except AttributeError:
            pass

        return export


class ExcelExporterMixin(ExporterMixin):
    content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    export_format = Export.FORMAT_XLSX
    export_context = Export.CONTEXT_LIST
    FORMATS = {
        'bold': {'bold': True},
        'header': {'bold': True, 'font_color': '#ffffff', 'bg_color': '#E2105D'},
        'date': {'num_format': 'dd.mm.yyyy'},
        'datetime': {'num_format': 'dd.mm.yyyy hh:mm'},
        'integer': {'num_format': '#'},
        'money': {'num_format': '### ### ###.00 €'},
        'bold_money': {'num_format': '### ### ###.00 €', 'bold': True},
    }
    proxy_class = None
    exclude_in_permission_widget = False

    @staticmethod
    def selectable_fields():
        raise NotImplementedError()

    def __init__(self, **kwargs):
        self.selected_fields = kwargs.get('selected_fields', None)
        super().__init__(**kwargs)

        # create a workbook in memory
        import xlsxwriter
        self.workbook = xlsxwriter.Workbook(self.output)
        self.workbook.remove_timezone = True

        # Add formats
        self.formats = {}
        for label, format in self.FORMATS.items():
            self.formats[label] = self.workbook.add_format(format)

    def get_worksheet_title(self, index=0):
        raise NotImplementedError()

    @staticmethod
    def to_excel_datetime(to_convert):
        from xlsxwriter.utility import datetime_to_excel_datetime
        return datetime_to_excel_datetime(to_convert, False, False)

    def export(self):
        self.write_data(self.workbook.add_worksheet(self.get_worksheet_title()))
        self.workbook.close()

    def get_attribute(self, field):
        return field[0]

    def get_label(self, field):
        return field[1]

    def get_column_width(self, field):
        return field[2]

    def get_cell_format(self, field):
        try:
            return field[3]
        except IndexError:
            return None

    def get_function(self, field):
        return field[4]

    def write_row(self, worksheet, row, col, obj, field):
        attr_index = None
        attr = self.get_attribute(field)

        if '[' in attr and ']' in attr:
            start = attr.rindex('[')
            end = attr.rindex(']')
            attr_index = attr[start+1:end]
            attr = attr[0:start]

        # get cell format
        cell_format_identifier = self.get_cell_format(field)
        cell_format = self.formats.get(cell_format_identifier, None)

        # get object attribute
        try:
            if isinstance(obj, dict):
                value = obj.get(attr)
            else:
                value = operator.attrgetter(attr)(obj)
        except AttributeError as e:
            if 'NoneType' in str(e):
                value = None
            else:
                raise e

        if attr_index and value is not None:
            value = value.get(attr_index, '')

        # try to use custom lambda handler
        try:
            func = self.get_function(field)
            value = func(value, obj)
        except TypeError:
            value = func(value)
        except IndexError:
            pass

        if isinstance(value, tuple) and isinstance(value[0], str):
            # formula
            formula, value = value
            worksheet.write_formula(row, col, formula, cell_format, value)
        else:
            # datetime
            if isinstance(value, datetime.datetime):
                value = localtime(value)

            if cell_format_identifier and 'date' in cell_format_identifier and value:
                # date or datetime format
                worksheet.write_datetime(row, col, value, cell_format)
            else:
                try:
                    # inherited string format
                    worksheet.write(row, col, value, cell_format)
                except TypeError:
                    # force string format
                    worksheet.write(row, col, str(value), cell_format)

    def get_queryset(self):
        raise NotImplementedError()

    def write_header(self, worksheet, fields, iterative_sets_fields):
        last_col = 0

        for field in fields:
            col_index = last_col
            attr = self.get_attribute(field)

            if hasattr(self, 'header_update') and attr in self.header_update.keys():
                label = self.header_update[attr]
            else:
                label = self.get_label(field)

            column_width = self.get_column_width(field)
            worksheet.write(0, col_index, label, self.formats['header'])
            worksheet.set_column(col_index, col_index, column_width)
            last_col += 1

        for iter_set in iterative_sets_fields:
            for iteration_index in range(1, iter_set['iteration_number'] + 1):
                for field in iter_set['fields']:
                    col_index = last_col
                    attr = self.get_attribute(field)
                    set_attr = iter_set['set_attr']

                    if hasattr(self, 'header_update') and set_attr in self.header_update.keys() and attr in self.header_update[set_attr]:
                        label = '{} #{}: {}'.format(iter_set['verbose_name'], iteration_index, self.header_update[set_attr][attr])
                    else:
                        label = '{} #{}: {}'.format(iter_set['verbose_name'], iteration_index, self.get_label(field))

                    worksheet.write(0, col_index, label, self.formats['header'])
                    worksheet.set_column(col_index, col_index, self.get_column_width(field))
                    last_col += 1

    def write_content(self, worksheet, fields, iterative_sets_fields, objects):
        # Write actual data. Start from the first cell. Rows and columns are zero indexed.
        row = 1
        max_col = 0

        for obj in objects:
            col = 0

            for field in fields:
                if self.proxy_class:
                    obj.__class__ = self.proxy_class
                self.write_row(worksheet, row, col, obj, field)
                col += 1

            for iter_set in iterative_sets_fields:
                for relative in getattr(obj, iter_set['set_attr']).all():
                    for field in iter_set['fields']:
                        self.write_row(worksheet, row, col, relative, field)
                        col += 1

            max_col = max(col, max_col)
            row += 1

        worksheet.autofilter(0, 0, row-1, max_col-1)

    def get_selected_fields(self, objects):
        fields = []

        for field_set in self.selectable_fields().values():
            for field in field_set:
                attr = self.get_attribute(field)
                if self.selected_fields is None or attr in self.selected_fields:
                    fields.append(field)

        iterative_sets_fields = []

        if hasattr(self, 'selectable_iterative_sets'):
            for set_attribute in self.selectable_iterative_sets().keys():
                # get number of iterations
                relatives_name = set_attribute[:-4]

                object_with_max_relatives = objects.annotate(
                    num_relatives=Count(relatives_name)
                ).order_by('-num_relatives')[0]
                iteration_number = object_with_max_relatives.num_relatives

                iterative_fields = []
                for field_set in self.selectable_iterative_sets()[set_attribute].values():
                    for field in field_set:
                        if self.get_attribute(field) in self.selected_fields:
                            iterative_fields.append(field)

                relatives_verbose_name = getattr(object_with_max_relatives, set_attribute).first()._meta.verbose_name

                iterative_sets_fields.append({
                    'set_attr': set_attribute,
                    'fields': iterative_fields,
                    'iteration_number': iteration_number,
                    'verbose_name': relatives_verbose_name,
                })

        return fields, iterative_sets_fields

    def write_data(self, worksheet):
        # get data
        objects = self.get_queryset()

        if not objects.exists():
            return

        # use only selected fields
        fields, iterative_sets_fields = self.get_selected_fields(objects)

        # write header and set columns width
        self.write_header(worksheet, fields, iterative_sets_fields)

        # write content
        self.write_content(worksheet, fields, iterative_sets_fields, objects)

        # write header and content for fields requiring iteration over multiple related objects if there are any
        # self.write_iterative_sets(worksheet, fields, objects)
