# Mixins

All mixins live in `outputs.mixins`. Exporters are assembled by combining them; views gain export behaviour the same way.

## Exporter mixins

### `ExporterMixin`

The base for every exporter. It is **model-based**: every concrete exporter is tied to a Django model either through a class-level `queryset` (preferred) or an explicit `model` attribute. This lets the mixin automatically resolve the model for admin labels, widget metadata, content-type tracking in `save_export()`, and the auto-generated `description`.

It also initialises an in-memory `BytesIO` output stream and provides the scaffolding that the rest of the system depends on.

Class attributes to set on subclasses:

| Attribute | Default | Description |
|---|---|---|
| `queryset` | `None` | Optional base queryset for the exporter; if set, its `.model` is used for metadata such as descriptions |
| `model` | `None` | Optional Django model class; used when you don't have or don't want to keep a concrete queryset on the class |
| `filename` | `None` | Output filename (accents are stripped automatically) |
| `description` | `''` | Human-readable label shown in admin; if empty, a generic label is auto-generated from the resolved model, format and context |
| `export_format` | `None` | One of `Export.FORMAT_XLSX`, `FORMAT_XML`, `FORMAT_PDF` |
| `export_context` | `None` | One of `Export.CONTEXT_LIST`, `CONTEXT_STATISTICS`, `CONTEXT_DETAIL` |
| `output_type` | `FILE` | `Export.OUTPUT_TYPE_FILE` or `OUTPUT_TYPE_STREAM` |
| `send_separately` | `False` | Send one email per recipient instead of a single email to all |
| `content_type` | `application/force-download` | HTTP content-type / MIME type of the output |

`ExporterMixin.get_model()` returns either `queryset.model` (when a queryset is defined) or the explicit `model` attribute. `get_app_and_model()` then exposes the resolved app label and model name for use in widgets and admin filters. `get_description()` uses the same resolution logic to build a generic label:

```python
f"{cls.__name__} ({model_name}, {export_format}, {export_context})"
```

unless you override `description` on the subclass, in which case that string is used verbatim.

Key methods to implement or override:

- **`export()`** – Generate output and write it to `self.output`.
- **`write_data(output)`** – Called by `export()`; receives the format-specific output object (e.g. xlsxwriter worksheet).
- **`get_message_body(count, file_url=None)`** – Return the HTML email body sent to recipients.
- **`get_message_subject()`** – Return a custom email subject, or `None` to use the default.
- **`export_to_response()`** – Calls `export()` and returns an `HttpResponse` with the file attached; useful for synchronous streaming exports.
- **`save_export()`** – Persists an `Export` record and `ExportItem` records to the database; called by `execute_export()` before enqueuing the mail job.

---

### `FilterExporterMixin`

Inherits from `ExporterMixin` and adds [django-filter](https://django-filter.readthedocs.io/) support so the exported queryset matches whatever filters the user applied in the UI. Because it extends `ExporterMixin` directly, it already carries the model-resolution logic: the `queryset` set on the subclass is used both to initialise the filter and as the model source for `get_model()`, `get_description()`, and `save_export()`.

Class attributes:

| Attribute | Description |
|---|---|
| `queryset` | Base queryset for the model being exported (also used by `ExporterMixin.get_model()` if defined) |
| `filter_class` | A `django_filters.FilterSet` subclass |
| `model` | Optional explicit model reference when you don't want to keep a queryset on the class |

Both `queryset` and `filter_class` can be overridden at instantiation time by passing them as keyword arguments, which lets a single exporter class serve multiple filtered views:

```python
exporter = OrderExporter(
    params=request.GET,
    queryset=Order.objects.filter(shop=request.user.shop),
    filter_class=ShopOrderFilter,
    user=request.user,
    recipients=[request.user],
)
```

`get_queryset()` returns the filter's queryset. If an `items` list is passed (e.g. when re-sending a previously saved export), it restricts the queryset to those PKs instead of re-applying the filter.

If the query string contains a `proxy` parameter, `get_whole_queryset()` calls `.proxy(proxy)` on the queryset, enabling proxy-model-scoped exports.

`get_message_body()` renders `outputs/export_message_body.html` and passes the active filter's human-readable field values into the template context.

---

### `ExcelExporterMixin`

Extends `ExporterMixin` to produce XLSX files via [xlsxwriter](https://xlsxwriter.readthedocs.io/). Sets `export_format = FORMAT_XLSX` and `export_context = CONTEXT_LIST` by default.

Subclasses **must** implement:

- **`selectable_fields()`** *(static)* – Returns a dict of `{ group_label: [field_tuple, ...] }`. Each field tuple is:
  ```
  (attribute, header_label, column_width [, cell_format [, transform_func]])
  ```
    - `attribute` – dotted attribute path on the object, e.g. `'customer.name'`. A `[key]` suffix reads from a dict: `'metadata[color]'`.
    - `cell_format` – optional key into the built-in format table (see below).
    - `transform_func` – optional callable `func(value[, obj])` applied after attribute lookup. Return a `(formula_string, fallback_value)` tuple to write an Excel formula.
- **`get_worksheet_title(index=0)`** – Returns the worksheet tab name.
- **`get_queryset()`** – Returns the queryset to export (typically delegated to `FilterExporterMixin`).

Optional:

- **`selectable_iterative_sets()`** – Returns a dict of `{ related_manager_attr: { group_label: [field_tuple, ...] } }`. Used to expand one-to-many relationships into repeated column groups (e.g. order lines). The number of column groups is determined dynamically from the object with the most related records.
- **`header_update`** (dict) – Override column headers at the instance level without changing `selectable_fields()`. Keys are attribute names; values are replacement labels. For iterative sets, the value is itself a dict of `{ attr: label }`.
- **`proxy_class`** – If set, each object's `__class__` is reassigned to this proxy class before reading attributes, enabling method dispatch on a proxy model.

Built-in cell formats (pass as the 4th element of a field tuple):

| Key | Format |
|---|---|
| `bold` | Bold text |
| `header` | Bold white text on red background (used for the header row automatically) |
| `date` | `dd.mm.yyyy` |
| `datetime` | `dd.mm.yyyy hh:mm` |
| `time` | `hh:mm` |
| `integer` | No decimal places |
| `percent` | `0.00%` |
| `money` | `### ### ##0.00 €` |
| `bold_money` | Same as `money` but bold |
| `money_amount` | `### ### ##0.00` (no currency symbol) |
| `bold_money_amount` | Same as `money_amount` but bold |

Content is written in parallel using `ThreadPoolExecutor` (controlled by `OUTPUTS_NUMBER_OF_THREADS`) when the queryset is large enough. The worksheet gets autofilter and frozen header row applied automatically.

---

## View mixins

### `ConfirmExportMixin`

Adds a confirmation step to any `FormView`. Renders `outputs/export_confirmation.html`, which shows the number of records that will be exported and a confirm button. On submit it triggers the async export and displays a flash message.

```python
from django.views.generic import FormView
from outputs.mixins import ConfirmExportMixin
from myapp.exporters import OrderExporter

class OrderExportView(ConfirmExportMixin, FormView):
    exporter_class = OrderExporter
    back_url = '/orders/'   # fallback; can also be passed via ?back_url= GET param
```

The `back_url` is resolved from the `back_url` GET parameter first, then from the class attribute. It is passed to the template as context and used as the success redirect URL.

Override `exporter_params` (property) to customise the keyword arguments forwarded to the exporter constructor.

---

### `SelectExportMixin`

Extends `ConfirmExportMixin` with a field-selection step. Uses `ChooseExportFieldsForm` and renders `outputs/export_selection.html`. The form is populated from the exporter's `selectable_fields()` and `selectable_iterative_sets()`.

```python
from outputs.mixins import SelectExportMixin
from myapp.exporters import OrderExporter

class OrderSelectExportView(SelectExportMixin, FormView):
    exporter_class = OrderExporter
    back_url = '/orders/'
```

Field visibility is permission-controlled: superusers see every field; regular users see only the fields permitted by their `export_fields_permissions` user attribute and by the `export_fields_permissions` JSON stored on their group metadata.

---

### `ExportFieldsPermissionsMixin`

A helper mixin used internally by `SelectExportMixin` to manage per-user/per-group field permissions. Permissions are stored as JSON dictionaries keyed by exporter dotted path, with lists of allowed field attribute names as values.

Useful methods if you need to manipulate permissions programmatically:

- **`load_export_fields_permissions(permissions)`** – Accepts a string, list, or queryset of raw JSON permission values and returns a list of parsed dicts.
- **`combine_export_fields_permissions(permissions)`** – Merges a list of permission dicts into a single dict (union of all allowed fields per exporter).
- **`substract_export_fields_permissions(first, second)`** – Returns `first − second`: fields allowed in `first` but not in `second`.

---

## Building an exporter

Every exporter is **model-based**. Setting `queryset` (or `model`) on the class is the first step; the mixin uses it to track the content type, build `save_export()` records, populate admin/widget labels, and (when combined with `FilterExporterMixin`) seed the django-filter queryset.

A typical XLSX list exporter combining `FilterExporterMixin` and `ExcelExporterMixin`:

```python
import django_filters
from outputs.mixins import FilterExporterMixin, ExcelExporterMixin
from myapp.models import Order

class OrderFilter(django_filters.FilterSet):
    class Meta:
        model = Order
        fields = ['status', 'created']

class OrderExporter(FilterExporterMixin, ExcelExporterMixin):
    # model-based: queryset drives get_model(), get_description(), and the filter
    queryset = Order.objects.all()
    filter_class = OrderFilter
    filename = 'orders.xlsx'
    description = 'Orders export'  # optional; auto-generated from queryset.model if omitted

    def get_worksheet_title(self, index=0):
        return 'Orders'

    @staticmethod
    def selectable_fields():
        return {
            'Order': [
                # (attribute, header label, column width[, cell format[, transform func]])
                ('id',              'ID',       5),
                ('status',          'Status',   15),
                ('created',         'Date',     15, 'date'),
                ('total',           'Total',    12, 'money'),
                ('customer.name',   'Customer', 20),
                # transform function: receives (value, obj) or just (value,)
                ('is_paid', 'Paid', 8, None, lambda v: 'Yes' if v else 'No'),
            ]
        }
```

### Iterative sets (one-to-many columns)

When an object has a variable number of related records (e.g. order lines), define `selectable_iterative_sets()` to expand them into repeated column groups. The number of groups is determined automatically from the object with the most relations:

```python
@staticmethod
def selectable_iterative_sets():
    return {
        'lines_set': {   # related manager attribute name
            'Order line': [
                ('product.name', 'Product', 20),
                ('quantity',     'Qty',      6, 'integer'),
                ('price',        'Price',   12, 'money'),
            ]
        }
    }
```
