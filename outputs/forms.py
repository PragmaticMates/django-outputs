from crispy_forms.bootstrap import FormActions
from crispy_forms.layout import Layout, Row, Div, Fieldset, Submit
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.forms import BooleanField, CheckboxInput, TextInput, Textarea
from django.utils.translation import ugettext_lazy as _

from django.contrib.auth import get_user_model
from outputs.models import Scheduler, AbstractExport
from outputs.widgets import CheckboxSelectMultipleWithDisabled, Legend
from pragmatic.forms import SingleSubmitFormHelper


class ConfirmExportForm(forms.Form):
    recipients = forms.ModelMultipleChoiceField(
        label=_('Recipients'),
        queryset=get_user_model().objects.all(),
        # widget=UsersWidget(),
        required=True,
    )
    filename = forms.CharField(label=_('File name'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = SingleSubmitFormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(Row(
            Div('recipients', css_class='col-lg-3'),
            Div('filename', css_class='col-lg-3'),
        ))


class ChooseExportFieldsForm(ConfirmExportForm):
    select_all = BooleanField(label=_('Select all'), widget=CheckboxInput(attrs={'class': 'all'}), required=False)

    def __init__(self, *args, **kwargs):
        self.selectable_fields = kwargs.pop('selectable_fields')
        self.permitted_fields = kwargs.pop('permitted_fields', [])
        # necessary to reset dynamic fields, as they will be added again at page reload
        self.fields = {}

        super().__init__(*args, **kwargs)
        self.static_fields = list(self.fields.keys())

        self.prepare_fields()
        self.build_layouts()

        self.helper = SingleSubmitFormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(*self.layouts)

    def prepare_fields(self):
        if self.selectable_fields:
            field_index = 0
            for label, field_group in self.selectable_fields.items():
                choices = []
                for field in field_group:
                    # disable choice if user doesn't have permission
                    if self.permitted_fields == True or field[0] in self.permitted_fields:
                        choices.append(field[:2])
                    else:
                        choices.append((field[0], {'label': field[1], 'disabled': True}))

                choices = tuple(choices)
                initial = tuple([field[0] for field in field_group if self.permitted_fields == True or field[0] in self.permitted_fields ])
                field_key = 'field_group_{}'.format(field_index)
                self.fields[field_key] = forms.MultipleChoiceField(label='', widget=CheckboxSelectMultipleWithDisabled(attrs={'class': 'option'}), choices=choices, initial=initial, required=False)

                # group checkbox
                group_key = 'group_{}'.format(field_index)
                self.fields[group_key] = BooleanField(label=label, widget=CheckboxInput(attrs={'class': 'group-option'}), required=False)

                field_index += 1

    def build_layouts(self):
        static_fields_layout = [
            Row(
                Div('recipients', css_class='col-lg-3'),
                Div('filename', css_class='col-lg-3'),
            ),
        ]

        # build dynamic fields layout
        dynamic_fields_layout = []
        for field_key, field in self.fields.items():
            # if not static field
            if field_key.startswith('field') and field_key not in self.static_fields:
                group_key = field_key.strip('field_')

                dynamic_fields_layout.append(
                    Div(
                        Legend(group_key),
                        Div(field_key),
                        css_class='col-md-2 group'
                    )
                )

        if dynamic_fields_layout:
            static_fields_layout.append(
                Row(
                    Div('select_all', css_class='col-md-3'),
                ),
            )

        self.layouts = [
            *static_fields_layout,
            Row(*dynamic_fields_layout),
        ]

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data.pop('select_all')

        if self.selectable_fields:
            export_fields = []

            for key in list(cleaned_data.keys()):
                if key.startswith('group'):
                    cleaned_data.pop(key)
                elif key not in self.static_fields:
                    export_fields.append(cleaned_data[key])

            if not any(export_fields):
                raise forms.ValidationError(_('Select at least one option'))

        return cleaned_data


class SchedulerForm(forms.ModelForm):
    recipients = forms.ModelMultipleChoiceField(
        label=_('Recipients'),
        queryset=get_user_model().objects.all(),
        # widget=UsersWidget(),
        required=True,
    )

    content_type = forms.ModelChoiceField(label=_('content type'), queryset=ContentType.objects.order_by('model'))  # TODO: show only exportable content types

    class Meta:
        model = Scheduler
        fields = ('routine', 'is_active', 'language',
                  'content_type', 'fields',
                  'format', 'context',
                  'query_string', 'recipients')
        widgets = {
            'query_string': TextInput,
            'fields': Textarea
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['query_string'].help_text = _('filter')

        self.helper = SingleSubmitFormHelper()
        self.helper.layout = Layout(
            Row(
                Fieldset(
                    _('Objects'),
                    Row(
                        Div('content_type', css_class='col-md-4'),
                        Div('context', css_class='col-md-4'),
                        Div('format', css_class='col-md-4'),
                        Div('query_string', css_class='col-md-12'),
                        Div('fields', css_class='col-md-12'),
                    ),
                    css_class='col-md-4'
                ),
                Fieldset(
                    _('Management'),
                    'recipients',
                    'routine',
                    'language',
                    'is_active',
                    css_class='col-md-2'
                )
            ),
            FormActions(
                Submit('submit', _('Submit'), css_class='btn-lg')
            )
        )

    def clean(self):
        context = self.cleaned_data.get('context', None)
        format = self.cleaned_data.get('format', None)
        content_type = self.cleaned_data.get('content_type', None)

        if context and format and content_type:
            model_class = content_type.model_class()

            try:
                # validation of content_type, context and format (check if exporter exists)
                AbstractExport.get_exporter_class(model_class, context, format)
            except ImportError:
                self.add_error(None, _('Exporter for content type {} with given context and format is not available').format(content_type))

        return self.cleaned_data
