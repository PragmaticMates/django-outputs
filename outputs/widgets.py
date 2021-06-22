import json
from collections import OrderedDict

from crispy_forms.layout import Field, Div
from crispy_forms.utils import TEMPLATE_PACK
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.forms import CheckboxSelectMultiple, MultipleChoiceField
from django.forms.widgets import ChoiceWidget
from django.template.loader import get_template
from django.utils.safestring import mark_safe
try:
    # Django 3.1
    from django.db.models import JSONField
except ImportError:
    # older Django
    from django.contrib.postgres.fields import JSONField


class ExportFieldsPermissionsMixin(object):
    def get_choices(self):
        if not self.choices:
            self.choices = self.load_choices()
        return self.choices

    def get_all_exportable_fields(self):
        if not hasattr(self, 'all_exportable_fields'):
            self.load_all_exportable_fields()
        return self.all_exportable_fields

    def get_max_field_groups(self):
        if not hasattr(self, 'max_field_groups'):
            self.load_all_exportable_fields()
        return self.max_field_groups

    def get_table(self):
        if not hasattr(self, 'table'):
            self.load_table_and_width()
        return self.table

    def get_table_width(self):
        if not hasattr(self, 'table'):
            self.load_table_and_width()
        return self.table_width

    def load_choices(self):
        choices = []

        # we are starting with dictionary to guarantee ordered vertical structure of the table
        table = self.get_table()

        for row in table:
            choices.append(row['exporter_key'])

            for group in row['field_groups']:
                # row may contain empty groups to fill up empty columns, skipping those here
                if group:
                    choices.append(group['key'])

                    for permission in group['permissions']:
                        choices.append(permission['key'])

        return choices

    def load_table_and_width(self):
        table = []
        row = {}

        # we are starting with dictionary to guarantee ordered vertical structure of the table
        exportable_fields = self.get_all_exportable_fields()
        max_field_groups = self.get_max_field_groups()

        for app, models in exportable_fields.items():
            row['app'] = app

            for model, formats in models.items():
                row['model'] = model

                for format, field_groups in formats.items():
                    row['format'] = format if len(formats) > 1 else None
                    row['exporter_key'] = '.'.join([app, model, format])
                    row['field_groups'] = []

                    index = 0
                    for group, fields in field_groups.items():
                        group_dict = {
                            'label': group,
                            'key': '/'.join([row['exporter_key'], 'group', str(index)]),
                            'permissions': []
                        }

                        for field in fields:
                            group_dict['permissions'].append({
                                'label': field[1],
                                'key': '/'.join([row['exporter_key'], field[0]]),
                            })

                        row['field_groups'].append(dict(group_dict))
                        index += 1

                    # fill the row with empty groups to have equal number of columns in every row
                    if index < max_field_groups:
                        for i in range(index, max_field_groups):
                            row['field_groups'].append({})

                    table.append(dict(row))

        self.table = table
        self.table_width = max_field_groups+1

    def load_all_exportable_fields(self):
        exporters = set()

        from outputs.mixins import ExcelExporterMixin
        for cls in ExcelExporterMixin.__subclasses__():
            if hasattr(cls, 'selectable_fields') and not cls.exclude_in_permission_widget:
                exporters.add(cls)

        all_exportable_fields = {}
        max_field_groups = 0

        for exporter in exporters:
            try:
                selectable_fields = exporter.selectable_fields()
            except AttributeError:
                selectable_fields = {}

            # enforcing order of dict in case it was unordered as it is crusial for the later use in table
            if not isinstance(selectable_fields, OrderedDict):
                selectable_fields = OrderedDict(selectable_fields)

            try:
                for iterative_set in exporter.selectable_iterative_sets().values():
                    selectable_fields.update(iterative_set)
            except AttributeError:
                pass

            app_name, model_name = exporter.get_model()._meta.label.split('.')
            export_format = exporter.export_format
            export_format = export_format.capitalize()

            # add app to dictionary of exportable fields if not there already, else update
            if app_name not in all_exportable_fields:
                all_exportable_fields[app_name] = {model_name: {}}
            elif model_name not in all_exportable_fields[app_name]:
                all_exportable_fields[app_name].update({model_name: {}})

            all_exportable_fields[app_name][model_name].update({
                export_format: selectable_fields
            })

            # looking for max number of groups which later translates to number of table columns
            if len(selectable_fields) > max_field_groups:
                max_field_groups = len(selectable_fields)

        self.all_exportable_fields = all_exportable_fields
        self.max_field_groups = max_field_groups

    def decompress(self, value):
        """
        Decompress value (expected to be string of json dumped dictionary) to list of initial values for template table
        """
        # is single value passed, convert to tuple, else raise error if not anticipated iterable
        if isinstance(value, str) or isinstance(value, dict):
            value = (value,)
        elif not isinstance(value, (list, tuple, QuerySet)):
            raise TypeError()

        exportable_fields = self.get_all_exportable_fields()
        permission_keys = set()

        for val in value:
            permissions = json.loads(val) if isinstance(val, str) else val
            # when val is retrieved from queryset, load needs to be done twice for some reason unknown to me
            if isinstance(permissions, str):
                permissions = json.loads(permissions)

            # due to previous bug this case is handled instead of creating migration
            if permissions is None:
                permissions={}
            # if two loads where not enough there gotta be something wrong
            elif not isinstance(permissions, dict):
                raise TypeError()

            for exporter_key, permitted_fields in permissions.items():
                for field in permitted_fields:
                    permission_keys.add('/'.join([exporter_key, field]))

                # set group and exporter fields
                app, model, format = exporter_key.split('.')
                exporter_fields_count = 0
                group_index = -1

                for group, group_fields in exportable_fields[app][model][format].items():
                    exporter_fields_count += len(group_fields)
                    group_index += 1
                    group_permitted_count = 0

                    for field in group_fields:
                        if field[0] not in permitted_fields:
                            break
                        group_permitted_count += 1

                    # if all fields within a group are permitted add group_key too (to initial values)
                    if group_permitted_count == len(group_fields):
                        permission_keys.add('/'.join([exporter_key, 'group', str(group_index)]))

                # if all fields of exporter are permitted add exporter_key too (to initial values)
                if len(permitted_fields) == exporter_fields_count:
                    permission_keys.add(exporter_key)

        return permission_keys

    def format_output(self, value, compress=True):
        """
        Converts value (list) to dictionary and optionally compress to json string
        """
        if not value:
            return {}

        output = {}
        for val in value:
            keys = val.split('/')
            # key length is supposed to be 1 for exporter, 2 for field, 3 for group
            if len(keys) > 3:
                raise ValueError()
            # we output only field values, exporter and group keys are only auxiliary
            elif len(keys) == 2:
                exporter_key = keys[0]
                field = keys[1]

                if exporter_key not in output:
                    output[exporter_key] = []

                output[exporter_key].append(field)

        # output dictionary compressed to string if compress=True and it is not empty
        if output and compress:
            return json.dumps(output)
        else:
            return output


class ExportFieldsPermissionsSelectMultipleWidget(CheckboxSelectMultiple, ExportFieldsPermissionsMixin):
    template = 'outputs/widgets/export_fields_permissions_widget.html'

    def __init__(self, attrs=None):
        super().__init__(attrs)

    def render(self, name, value, attrs=None, choices=(), renderer=None):
        t = get_template(self.template)

        # decompress value (json compressed dictionary) into list if exists, else pass empty tuple
        if value:
            value = self.decompress(value)
        else:
            value = ()

        c = {
            'name': name,
            'value': value,
            'table': self.get_table(),
            'width': self.get_table_width(),
        }

        return mark_safe(t.render(c))


class ExportFieldsPermissionsField(MultipleChoiceField):
    """
    This Field is intended to be used with ExportFieldsPermissionsSelectMultipleWidget,
    without it ExportFieldsPermissionsSelectMultipleWidget's render method needs to be implemented
    """
    widget = ExportFieldsPermissionsSelectMultipleWidget

    def __init__(self, *args, **kwargs):
        # widget.get_choices can't be used because exporters in widget.get_all_exportable_fields are not yet available
        super().__init__(*args, **kwargs)
        self.required=False

    def validate(self, value):
        """Validate that the input is a list or tuple."""
        if self.required and not value:
            raise ValidationError(self.error_messages['required'], code='required')

        if not isinstance(value, (list, tuple)):
            raise TypeError()

        # Validate that each value in the value list is in self.choices.
        for val in value:
            if val not in self.choices:
                raise ValidationError(
                    self.error_messages['invalid_choice'],
                    code='invalid_choice',
                    params={'value': val},
                )

    def clean(self, value):
        # get choices for validation, at this point exporters are already available
        self.choices = self.widget.get_choices()

        # clean using modified validate() method
        value = self.to_python(value)
        self.validate(value)
        self.run_validators(value)
        return self.widget.format_output(value)


class ExportFieldsPermissionsModelField(JSONField):
    """
    Custom export fields permissions field based on JSONField
    """
    form_class = ExportFieldsPermissionsField

    def formfield(self, **kwargs):
        kwargs.update({'widget': self.form_class.widget})
        field = self.form_class(**kwargs)
        return field


class ExportFieldsPermissionsCrispyField(Field):
    template = 'outputs/widgets/export_fields_permissions_layout.html'

    def __init__(self, *args, **kwargs):
        self.initial = kwargs.pop('initial', None)
        self.initial_group_permissions = kwargs.pop('initial_group', None)
        super().__init__(*args, **kwargs)
        self.widget = ExportFieldsPermissionsSelectMultipleWidget()

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, extra_context=None, **kwargs):
        if extra_context is None:
            extra_context = {}

        extra_context['table'] = self.widget.get_table()
        extra_context['width'] = self.widget.get_table_width()

        # decompress initial value (json compressed dictionary) into list if exist, else pass empty tuple
        if self.initial:
            initial = self.widget.decompress(self.initial)
        else:
            initial = ()

        # decompress group permissions if there are any
        if self.initial_group_permissions:
            groups_permissions = self.widget.decompress(self.initial_group_permissions)
        else:
            groups_permissions = ()

        form.initial['export_fields_permissions'] = initial
        extra_context['groups_permissions'] = groups_permissions

        return super().render(form, form_style, context, template_pack, extra_context, **kwargs)


class CheckboxSelectMultipleWithDisabled(ChoiceWidget):
    """
    Subclass of Django's ChoiceWidget and based on ChcekboxSelectMultiple widget that allows disabling options according to https://djangosnippets.org/snippets/2453/.
    To disable an option, pass a dict instead of a string for its label,
    of the form: {'label': 'option label', 'disabled': True}
    """
    allow_multiple_selected = True
    input_type = 'checkbox'
    template_name = "outputs/widgets/custom_checkbox_select.html"
    option_template_name = 'django/forms/widgets/checkbox_option.html'

    def use_required_attribute(self, initial):
        # Don't use the 'required' attribute because browser validation would
        # require all checkboxes to be checked instead of at least one.
        return False

    def value_omitted_from_data(self, data, files, name):
        # HTML checkboxes don't appear in POST data if not checked, so it's
        # never known if the value is actually omitted.
        return False

    def id_for_label(self, id_, index=None):
        """"
        Don't include for="field_0" in <label> because clicking such a label
        would toggle the first checkbox.
        """
        if index is None:
            return ''
        return super().id_for_label(id_, index)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        disabled = False

        # call parent method with label and supply with disabled attribute afterwatds
        if isinstance(label, dict):
            label, disabled = label['label'], label['disabled']

        option_dict = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)

        if disabled:
            option_dict['attrs']['disabled'] = 'disabled'
        return option_dict


class Legend(Div):
    template = "outputs/widgets/legend.html"
