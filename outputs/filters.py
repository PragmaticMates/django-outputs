import django_filters
from crispy_forms.bootstrap import InlineRadios
from crispy_forms.layout import Layout, Row, Div, Fieldset, Field
from django.contrib.contenttypes.models import ContentType
from django.forms import HiddenInput
from django.utils.translation import ugettext_lazy as _
from django_select2.forms import Select2Widget
from django.contrib.auth import get_user_model
from outputs.models import Export, Scheduler
from pragmatic.forms import SingleSubmitFormHelper
from pragmatic.filters import SliderFilter


class ExportFilter(django_filters.FilterSet):
    created = django_filters.DateFromToRangeFilter()
    total = SliderFilter(label=_('Total items'), step=10, has_range=True, segment='outputs.Export.total')
    creator = django_filters.ModelChoiceFilter(queryset=get_user_model().objects.all(), widget=Select2Widget)
    content_type = django_filters.ModelChoiceFilter(
        queryset=ContentType.objects.filter(pk__in=Export.objects.order_by('content_type').values_list('content_type', flat=True).distinct()),
        widget=Select2Widget
    )

    class Meta:
        model = Export
        fields = [
            'id', 'created', 'format', 'context', 'content_type', 'status',
            'total', 'creator'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.fields['format'].empty_label = _("Doesn't matter")
        self.form.fields['context'].empty_label = _("Doesn't matter")
        self.helper = SingleSubmitFormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        self.helper.layout = Layout(
            Row(
                Div(
                    Row(
                        Fieldset(
                            _('Generic'),
                            Row(
                                Div('id', css_class='col-md-4'),
                                Div(Field('created', css_class='date-picker form-control'), css_class='col-md-8 range-filter')
                            ),
                            css_class='col-md-12'
                        ),
                    ),
                    Row(
                        Fieldset(
                            _('Related'),
                            Row(
                                Div('creator', css_class='col-md-5'),
                                Div(Field('total', css_class='form-control'), css_class='col-md-7 range-filter')
                            ),
                            Row(
                                Div('content_type', css_class='col-md-5')
                            ),
                            css_class='col-md-12'
                        ),
                    ),
                    css_class='col-md-9'
                ),
                Fieldset(
                    _('Attributes'),
                    InlineRadios('format'),
                    InlineRadios('context'),
                    css_class='col-md-3'
                ),
            )
        )


class ExportFilterSet(django_filters.FilterSet):
    export = django_filters.ModelChoiceFilter(queryset=Export.objects.all(), widget=HiddenInput(), label=_('Export'), method='filter_export')

    def filter_export(self, queryset, name, value):
        return queryset.filter(id__in=value.object_list)


class SchedulerFilter(django_filters.FilterSet):
    created = django_filters.DateFromToRangeFilter()
    creator = django_filters.ModelChoiceFilter(queryset=get_user_model().objects.all(), widget=Select2Widget)
    content_type = django_filters.ModelChoiceFilter(
        queryset=ContentType.objects.filter(pk__in=Scheduler.objects.order_by('content_type').values_list('content_type', flat=True).distinct()),
        widget=Select2Widget
    )
    is_active = django_filters.ChoiceFilter(label=_('Active'), empty_label=_("Doesn't matter"), choices=[('True', _("Yes")), ('False', _("No"))])

    class Meta:
        model = Scheduler
        fields = [
            'id', 'created', 'format', 'context', 'content_type',
            'creator', 'routine', 'is_active'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.fields['format'].empty_label = _("Doesn't matter")
        self.form.fields['context'].empty_label = _("Doesn't matter")
        self.helper = SingleSubmitFormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        self.helper.layout = Layout(
            Row(
                Div(
                    Row(
                        Fieldset(
                            _('Generic'),
                            Row(
                                Div('id', css_class='col-md-4'),
                                Div(Field('created', css_class='date-picker form-control'), css_class='col-md-8 range-filter')
                            ),
                            css_class='col-md-12'
                        ),
                    ),
                    Row(
                        Fieldset(
                            _('Related'),
                            Row(
                                Div('creator', css_class='col-md-5'),
                                Div(Field('total', css_class='form-control'), css_class='col-md-7 range-filter')
                            ),
                            Row(
                                Div('content_type', css_class='col-md-5')
                            ),
                            css_class='col-md-12'
                        ),
                    ),
                    css_class='col-md-9'
                ),
                Fieldset(
                    _('Attributes'),
                    InlineRadios('format'),
                    InlineRadios('context'),
                    InlineRadios('routine'),
                    InlineRadios('is_active'),
                    css_class='col-md-3'
                ),
            )
        )
