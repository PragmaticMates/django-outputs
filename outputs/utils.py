def serialize_exporter_params(params: dict) -> dict:
    """
    Convert ORM objects in exporter_params to safe primitives for job queuing.

    Transforms:
      - ``user``       -> ``user_id`` (int | None)
      - ``recipients`` -> ``recipient_ids`` (list[int])
      - ``queryset``   -> ``queryset_ids`` (list[int]) + ``queryset_model`` (dotted
                          app_label.model_name), **only when a queryset is present**.
                          When queryset is absent the keys are omitted entirely so
                          the deserialized dict keeps the same shape the exporter
                          constructor expects.

    All other keys are passed through unchanged (e.g. ``params``, ``filename``,
    ``selected_fields``, ``url``, …).
    """
    from django.db.models import QuerySet

    serialized = dict(params)

    # user
    user = serialized.pop('user', None)
    if user is None:
        serialized['user_id'] = None
    else:
        serialized['user_id'] = getattr(user, 'pk', user)

    # recipients (queryset or list of user objects)
    recipients = serialized.pop('recipients', [])
    serialized['recipient_ids'] = [getattr(r, 'pk', r) for r in recipients]

    # queryset — only serialize when actually present; omit keys otherwise so
    # exporter constructors that don't accept queryset don't receive an
    # unexpected queryset=None kwarg.
    queryset = serialized.pop('queryset', None)
    if queryset is not None and isinstance(queryset, QuerySet):
        serialized['queryset_ids'] = list(queryset.values_list('pk', flat=True))
        serialized['queryset_model'] = (
            f"{queryset.model._meta.app_label}.{queryset.model._meta.model_name}"
        )

    return serialized


def deserialize_exporter_params(params: dict) -> dict:
    """
    Reconstruct ORM objects from the serialized primitives produced by
    :func:`serialize_exporter_params`.

    Re-fetches ``user`` and ``recipients`` fresh from the database.
    Rebuilds ``queryset`` as a ``pk__in`` queryset only when
    ``queryset_ids`` / ``queryset_model`` keys are present in *params*.
    """
    from django.apps import apps
    from django.contrib.auth import get_user_model

    deserialized = dict(params)
    User = get_user_model()

    # user
    user_id = deserialized.pop('user_id', None)
    deserialized['user'] = User.objects.get(pk=user_id) if user_id is not None else None

    # recipients
    recipient_ids = deserialized.pop('recipient_ids', [])
    deserialized['recipients'] = list(User.objects.filter(pk__in=recipient_ids))

    # queryset — only reconstruct when keys are present
    if 'queryset_ids' in deserialized and 'queryset_model' in deserialized:
        queryset_ids = deserialized.pop('queryset_ids')
        queryset_model = deserialized.pop('queryset_model')
        app_label, model_name = queryset_model.split('.')
        model = apps.get_model(app_label, model_name)
        deserialized['queryset'] = model.objects.filter(pk__in=queryset_ids)
    # If the keys are absent, 'queryset' is simply not included in the result.

    return deserialized
