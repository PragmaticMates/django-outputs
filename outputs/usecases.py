import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.utils import translation

from outputs import settings as outputs_settings

try:
    # older Django
    from django.utils.translation import ugettext_lazy as _
except ImportError:
    # Django >= 3
    from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


def execute_export(exporter, language):
    try:
        # save export to DB
        export = exporter.save_export()
        logger.info(f"Export created: export_id={export.id}, total_items={export.total}")

        # send mail with export to recipients
        export.send_mail(language, exporter.get_filename())
    except Exception as e:
        logger.error(f"Failed to execute export: exporter_class={exporter.__class__}, error={str(e)}", exc_info=True)
        raise


def export_items(export, language, filename=None):
    """
    Process export items and generate export file.
    
    Uses database transactions to ensure data consistency.
    Updates ExportItem status based on export success/failure.
    """
    from django.db import transaction
    from outputs.models import Export, ExportItem

    logger.info(
        f"Processing export items: export_id={export.id}, "
        f"content_type={export.content_type}, total_items={export.total}"
    )

    export.status = Export.STATUS_PROCESSING
    export.save(update_fields=['status'])

    # set language
    translation.activate(language)

    exporter = export.exporter

    # get queryset via Export items
    exporter.items = export.object_list

    try:
        with transaction.atomic():
            exporter.export()
            export.status = Export.STATUS_FINISHED
            export.save(update_fields=['status'])
            updated_count = export.update_export_items_result(ExportItem.RESULT_SUCCESS)
            logger.info(
                f"Updated {updated_count} ExportItem records to SUCCESS for export_id={export.id}"
            )
        mail_successful_export(export, filename, exporter.get_output())
    except Exception as e:
        with transaction.atomic():
            export.status = Export.STATUS_FAILED
            export.save(update_fields=['status'])
            updated_count = export.update_export_items_result(ExportItem.RESULT_FAILURE, detail=str(e))
            logger.info(
                f"Updated {updated_count} ExportItem records to FAILURE for export_id={export.id}"
            )
        notify_about_failed_export(export, str(e))
           

def notify_about_failed_export(export, error_detail):
    logger.error(
        f"Export generation failed: export_id={export.id}, "
        f"creator={export.creator}, error={error_detail}",
        exc_info=True
    )

    # details
    details = '{}: {}\n'.format(_('Creator'), export.creator)
    details += '{}: {}\n\n'.format(_('Export ID'), str(export.id))
    details += '{}: {}\n'.format(_('Error'), error_detail)

    if 'whistle' in settings.INSTALLED_APPS:
        from whistle.helpers import notify

        notify_users = get_user_model().objects \
            .active() \
            .filter(
            Q(is_superuser=True) |
            Q(pk=export.creator.pk) |
            Q(pk__in=export.recipients.all())
        ).distinct()

        # notify creator, recipients and superusers about failed export
        for user in notify_users:
            notify(recipient=user, event='EXPORT_FAILED', object=export, target=export.content_type, details=details)

    raise


def mail_successful_export(export, filename=None, output_file=None):
    exporter = export.exporter

    if outputs_settings.SAVE_AS_FILE:
        # Save the export using Django's default storage
        output_filename = filename or exporter.get_filename()
        file_path = f'exports/{output_filename}'

        # Save the file using default storage
        file_content = ContentFile(output_file or exporter.get_output())
        saved_path = default_storage.save(file_path, file_content)
        logger.info(f"Export file saved: export_id={export.id}, saved_path={saved_path}")

        # Get the full URL if the storage backend supports it
        try:
            file_url = default_storage.url(saved_path)
        except NotImplementedError:
            file_url = saved_path
    else:
        file_url = None

    verbose_name = export.content_type.model_class()._meta.verbose_name_plural

    # get total number of exported items
    num_items = export.total

    if export.send_separately:
        logger.info(
            f"Sending export emails separately: export_id={export.id}, "
            f"recipients_count={len(export.recipients_emails)}"
        )
        for recipient in export.recipients_emails:
            message = get_message(
                exporter,
                count=num_items,
                recipient_list=[recipient],
                subject='{}: {}'.format(_('Export'), verbose_name),
                output_file=output_file,
                filename=filename,
                file_url=file_url
            )

            # send
            message.send(fail_silently=False)

    else:
        logger.info(
            f"Sending export email to all recipients: export_id={export.id}, "
            f"recipients_count={len(export.recipients_emails)}"
        )
        message = get_message(
            exporter,
            count=num_items,
            recipient_list=export.recipients_emails,
            subject='{}: {}'.format(_('Export'), verbose_name),
            output_file=output_file,
            filename=filename,
            file_url=file_url
        )
        # send
        message.send(fail_silently=False)

    logger.info(f"Export completed: export_id={export.id}, recipients={len(export.recipients_emails)}")


def get_message(exporter, count, recipient_list, subject, output_file=None, filename=None, file_url=None):
    # message body
    body = exporter.get_message_body(count, file_url)

    # message subject
    subject = exporter.get_message_subject() or subject

    # prepare message
    message = EmailMultiAlternatives(subject=subject, to=recipient_list)
    message.attach_alternative(body, "text/html")

    if count > 0 and file_url is None:
        # get the stream and set the correct mimetype
        message.attach(
            filename or exporter.get_filename(),
            output_file or exporter.get_output(),
            exporter.content_type
        )

    return message