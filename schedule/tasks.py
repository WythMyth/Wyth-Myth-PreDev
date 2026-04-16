import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

from .models import MeetingEmailSchedule, MeetingSchedule

User = get_user_model()
logger = logging.getLogger(__name__)

NOTICE_LABELS = {
    "3w": "3 Weeks",
    "2w": "2 Weeks",
    "1w": "1 Week",
    "1d": "1 Day",
    "10m": "10 Minutes",
}


# ── Legacy task – kept so Beat doesn't throw KeyError, does nothing ────────
@shared_task
def check_meeting_reminders():
    return "disabled"


# ── Main notice dispatcher ─────────────────────────────────────────────────
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_meeting_notice(self, meeting_id: int, notice_type: str):
    """
    ETA-based task triggered by notifications.schedule_meeting_notifications.
    Queues one send_individual_notice task per active user.
    """
    try:
        meeting = MeetingSchedule.objects.get(pk=meeting_id)
    except MeetingSchedule.DoesNotExist:
        logger.warning(f"send_meeting_notice: meeting {meeting_id} not found.")
        return

    if not meeting.enable_all_email_notification:
        return

    # Idempotency check
    schedule = MeetingEmailSchedule.objects.filter(
        meeting_id=meeting_id, notice_type=notice_type
    ).first()
    if schedule and schedule.is_sent:
        return

    tags = meeting.guests.all()
    if not tags.exists():
        return
    recipients = (
        User.objects.filter(is_active=True, tags__in=tags)
        .exclude(email__isnull=True)
        .exclude(email__exact="")
        .distinct()
    )
    if not recipients.exists():
        logger.info(f"No recipients for meeting {meeting_id}.")
        return

    for user in recipients:
        send_individual_notice.delay(user.id, meeting_id, notice_type)

    logger.info(
        f"Queued '{notice_type}' for {recipients.count()} users – meeting {meeting_id}."
    )

    if schedule:
        schedule.is_sent = True
        schedule.save(update_fields=["is_sent"])


# ── Per-user email sender ──────────────────────────────────────────────────
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_individual_notice(self, user_id: int, meeting_id: int, notice_type: str):
    """
    Sends email to a single user for a meeting notice.
    Each task opens its own fresh SMTP connection to avoid
    SMTPServerDisconnected errors when many emails fire at once.
    """
    try:
        user = User.objects.get(pk=user_id)
        meeting = MeetingSchedule.objects.get(pk=meeting_id)
    except (User.DoesNotExist, MeetingSchedule.DoesNotExist) as e:
        logger.warning(f"send_individual_notice: {e}")
        return

    if not user.email:
        return

    label = NOTICE_LABELS.get(notice_type, notice_type)
    subject = f"[{label} Reminder] {meeting.title} – {meeting.date}"

    ctx = {
        "user": user,
        "meeting": meeting,
        "notice_type": notice_type,
        "notice_label": label,
    }

    try:
        text_body = render_to_string("emails/meeting_notice.txt", ctx)
        html_body = render_to_string("emails/meeting_notice.html", ctx)
    except Exception:
        text_body = (
            f"Dear {user.get_full_name() or user.email},\n\n"
            f"Reminder ({label}): {meeting.title}\n"
            f"Date: {meeting.date}\n"
            f"Start: {meeting.start_time}\n"
            f"URL: {meeting.meeting_url or 'N/A'}\n\n"
            f"HFall Team"
        )
        html_body = None

    try:

        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
            fail_silently=False,
            timeout=30,
        )

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            to=[user.email],
            connection=connection,
        )
        if html_body:
            msg.attach_alternative(html_body, "text/html")
        msg.send()
        logger.info(f"Sent '{notice_type}' to {user.email} for meeting {meeting_id}.")

    except Exception as exc:
        logger.error(f"Failed to send to {user.email}: {exc}")
        raise self.retry(exc=exc)


##last comment code
# import logging

# from celery import shared_task
# from django.conf import settings
# from django.contrib.auth import get_user_model
# from django.core.mail import EmailMultiAlternatives
# from django.template.loader import render_to_string
# from django.utils import timezone

# from .models import MeetingEmailSchedule, MeetingSchedule

# User   = get_user_model()
# logger = logging.getLogger(__name__)

# NOTICE_LABELS = {
#     "3w":  "3 Weeks",
#     "2w":  "2 Weeks",
#     "1w":  "1 Week",
#     "1d":  "1 Day",
#     "10m": "10 Minutes",
# }


# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def send_meeting_notice(self, meeting_id: int, notice_type: str):
#     """
#     ETA-based task – triggered by notifications.schedule_meeting_notifications.
#     Queues one send_individual_notice task per active user.
#     """
#     try:
#         meeting = MeetingSchedule.objects.get(pk=meeting_id)
#     except MeetingSchedule.DoesNotExist:
#         logger.warning(f"Meeting {meeting_id} not found.")
#         return

#     if not meeting.enable_all_email_notification:
#         return

#     # Idempotency check
#     schedule = MeetingEmailSchedule.objects.filter(
#         meeting_id=meeting_id, notice_type=notice_type
#     ).first()
#     if schedule and schedule.is_sent:
#         return

#     recipients = (
#         User.objects.filter(is_active=True)
#         .exclude(email__isnull=True)
#         .exclude(email__exact='')
#     )

#     if not recipients.exists():
#         logger.info(f"No recipients for meeting {meeting_id}.")
#         return


#     for user in recipients:
#         send_individual_notice.delay(user.id, meeting_id, notice_type)

#     logger.info(
#         f"Queued '{notice_type}' notice for {recipients.count()} "
#         f"users – meeting {meeting_id}."
#     )

#     # Mark as sent
#     if schedule:
#         schedule.is_sent = True
#         schedule.save(update_fields=["is_sent"])


# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def send_individual_notice(self, user_id: int, meeting_id: int, notice_type: str):
#     """
#     Sends email to a single user for a meeting notice.
#     """
#     try:
#         user    = User.objects.get(pk=user_id)
#         meeting = MeetingSchedule.objects.get(pk=meeting_id)
#     except (User.DoesNotExist, MeetingSchedule.DoesNotExist) as e:
#         logger.warning(f"send_individual_notice: {e}")
#         return

#     if not user.email:
#         return

#     label   = NOTICE_LABELS.get(notice_type, notice_type)
#     subject = f"[{label} Reminder] {meeting.title} – {meeting.date}"

#     ctx = {
#         "user":         user,
#         "meeting":      meeting,
#         "notice_type":  notice_type,
#         "notice_label": label,
#     }

#     try:
#         text_body = render_to_string("emails/meeting_notice.txt", ctx)
#         html_body = render_to_string("emails/meeting_notice.html", ctx)
#     except Exception:
#         text_body = (
#             f"Dear {user.get_full_name() or user.username},\n\n"
#             f"Reminder ({label}): {meeting.title}\n"
#             f"Date: {meeting.date}\n"
#             f"Start: {meeting.start_time}\n"
#             f"URL: {meeting.meeting_url or 'N/A'}\n\n"
#             f"HFall Team"
#         )
#         html_body = None

#     try:
#         msg = EmailMultiAlternatives(
#             subject=subject,
#             body=text_body,
#             from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
#             to=[user.email],
#         )
#         if html_body:
#             msg.attach_alternative(html_body, "text/html")
#         msg.send()
#         logger.info(
#             f"Sent '{notice_type}' to {user.email} for meeting {meeting_id}."
#         )
#     except Exception as exc:
#         logger.error(f"Failed to send to {user.email}: {exc}")
#         raise self.retry(exc=exc)
##last comment


# second comment start
# tasks.py
# ────────
# Celery tasks for meeting email notifications.

# Two systems coexist here:
#   1. Legacy poll-based reminders  (check_meeting_reminders, etc.)  – kept as-is.
#   2. New ETA-based notice system  (send_meeting_notice)            – new.
# """
# import logging

# import pytz
# from celery import shared_task
# from django.conf import settings
# from django.contrib.auth import get_user_model
# from django.core.mail import EmailMultiAlternatives, send_mail
# from django.template.loader import render_to_string
# from django.utils import timezone

# from .models import MeetingEmailSchedule, MeetingSchedule

# User   = get_user_model()
# logger = logging.getLogger(__name__)


# # ═══════════════════════════════════════════════════════════════════════════
# # LEGACY: poll-based reminders (10 min & 24 hr) – unchanged
# # ═══════════════════════════════════════════════════════════════════════════

# @shared_task
# def check_meeting_reminders():
#     ny_tz        = pytz.timezone('America/New_York')
#     current_time = timezone.now().astimezone(ny_tz)

#     meetings = MeetingSchedule.objects.filter(
#         is_expired=False,
#         date__gte=current_time.date(),
#     )

#     reminder_1440_count = 0
#     reminder_10_count   = 0

#     for meeting in meetings:
#         try:
#             if not meeting.datetime_combined:
#                 continue

#             if (
#                 meeting.reminder_24hr_time
#                 and meeting.reminder_24hr_time <= current_time < meeting.datetime_combined
#                 and not meeting.reminder_24hr_sent
#             ):
#                 send_meeting_reminder_email.delay(meeting.id, 1440)
#                 meeting.reminder_24hr_sent = True
#                 meeting.save()
#                 reminder_1440_count += 1

#             if (
#                 meeting.reminder_10min_time
#                 and meeting.reminder_10min_time <= current_time < meeting.datetime_combined
#                 and not meeting.reminder_10min_sent
#             ):
#                 send_meeting_reminder_email.delay(meeting.id, 10)
#                 meeting.reminder_10min_sent = True
#                 meeting.save()
#                 reminder_10_count += 1

#         except Exception as e:
#             logger.error(f"Error checking reminders for meeting {meeting.id}: {e}")

#     logger.info(
#         f"Total 1440-minute reminders: {reminder_1440_count}, "
#         f"10-minute reminders: {reminder_10_count}"
#     )
#     return (
#         f"{reminder_1440_count} (1440min) and "
#         f"{reminder_10_count} (10min) reminders sent."
#     )


# @shared_task
# def send_meeting_reminder_email(meeting_id: int, reminder_minutes: int):
#     try:
#         meeting = MeetingSchedule.objects.get(id=meeting_id)
#     except MeetingSchedule.DoesNotExist:
#         logger.error(f"Meeting with ID {meeting_id} not found.")
#         return "Meeting not found."

#     users = (
#         User.objects.filter(is_active=True)
#         .exclude(email__isnull=True)
#         .exclude(email__exact='')
#     )
#     for user in users:
#         send_individual_reminder.delay(user.id, meeting.id, reminder_minutes)

#     logger.info(
#         f"{reminder_minutes} min reminder scheduled for {users.count()} "
#         f"users for meeting {meeting.id}"
#     )
#     return f"{users.count()} reminders ({reminder_minutes} min) scheduled."


# @shared_task
# def send_individual_reminder(user_id: int, meeting_id: int, reminder_minutes: int):
#     try:
#         user    = User.objects.get(id=user_id)
#         meeting = MeetingSchedule.objects.get(id=meeting_id)

#         meeting_datetime = meeting.datetime_combined
#         formatted_time   = meeting_datetime.strftime('%I:%M %p') if meeting_datetime else "N/A"
#         formatted_date   = meeting.date.strftime('%d %B, %Y') if meeting.date else "N/A"

#         subject_prefix = (
#             "🔔 Final Reminder (10 min)" if reminder_minutes == 10
#             else "⏰ Reminder (24hr)"
#         )
#         subject = f"{subject_prefix}: {meeting.title}"

#         message = f"""
# Dear {user.get_full_name() or user.username},

# Assalamu Alaikum,

# This is a reminder for your upcoming meeting:

# 📅 Title:      {meeting.title}
# 📆 Date:       {formatted_date}
# ⏰ Start Time: {formatted_time}
# {f'📝 Description: {meeting.description}' if meeting.description else ''}
# {f'🔗 Meeting URL: {meeting.meeting_url}' if meeting.meeting_url else ''}
# {f'🔐 Password:    {meeting.password}' if meeting.password else ''}

# This is your {'10-minute' if reminder_minutes == 10 else '24-hour'} reminder.

# Best regards,
# HFall Team
# ---
# Automated Email. Please do not reply.
#         """

#         send_mail(
#             subject,
#             message,
#             settings.DEFAULT_FROM_EMAIL,
#             [user.email],
#             fail_silently=False,
#         )
#         logger.info(
#             f"Sent {reminder_minutes}-min reminder to {user.email} "
#             f"for meeting {meeting.id}"
#         )
#         return f"Email sent to {user.email}"

#     except Exception as e:
#         logger.error(
#             f"Error sending {reminder_minutes}-min reminder to user {user_id}: {e}"
#         )
#         return f"Error: {e}"


# # ═══════════════════════════════════════════════════════════════════════════
# # NEW: ETA-based notice system
# # ═══════════════════════════════════════════════════════════════════════════

# NOTICE_LABELS = {
#     "3w":  "3 Weeks",
#     "2w":  "2 Weeks",
#     "1w":  "1 Week",
#     "1d":  "1 Day",
#     "10m": "10 Minutes",
# }


# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def send_meeting_notice(self, meeting_id: int, notice_type: str):
#     """
#     Send an email notice to all active users for *meeting_id*.
#     Called via Celery ETA (scheduled by notifications.schedule_meeting_notifications).
#     """
#     try:
#         meeting = MeetingSchedule.objects.get(pk=meeting_id)
#     except MeetingSchedule.DoesNotExist:
#         logger.warning(f"send_meeting_notice: meeting {meeting_id} not found – skipping.")
#         return

#     # Master switch guard
#     if not meeting.enable_all_email_notification:
#         return

#     # Idempotency check
#     schedule = MeetingEmailSchedule.objects.filter(
#         meeting_id=meeting_id, notice_type=notice_type
#     ).first()
#     if schedule and schedule.is_sent:
#         return

#     # Gather recipients – all active users with an email address
#     recipients = (
#         User.objects.filter(is_active=True)
#         .exclude(email__isnull=True)
#         .exclude(email__exact='')
#     )
#     to_emails = [u.email for u in recipients if u.email]
#     if not to_emails:
#         logger.info(f"send_meeting_notice: no recipients for meeting {meeting_id}.")
#         return

#     label    = NOTICE_LABELS.get(notice_type, notice_type)
#     subject  = f"[{label} Reminder] {meeting.title} – {meeting.date}"

#     ctx = {
#         "meeting":      meeting,
#         "notice_type":  notice_type,
#         "notice_label": label,
#         "site_name":    getattr(settings, "SITE_NAME", "Meeting Portal"),
#         "site_url":     getattr(settings, "SITE_URL", ""),
#     }

#     # Render templates (create these in templates/emails/)
#     try:
#         text_body = render_to_string("emails/meeting_notice.txt", ctx)
#         html_body = render_to_string("emails/meeting_notice.html", ctx)
#     except Exception:
#         # Fallback plain-text if templates are missing
#         text_body = (
#             f"Reminder ({label}): {meeting.title}\n"
#             f"Date: {meeting.date}\n"
#             f"Start: {meeting.start_time}\n"
#             f"URL: {meeting.meeting_url or 'N/A'}\n"
#         )
#         html_body = None

#     msg = EmailMultiAlternatives(
#         subject=subject,
#         body=text_body,
#         from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
#         to=to_emails,
#     )
#     if html_body:
#         msg.attach_alternative(html_body, "text/html")

#     try:
#         msg.send()
#         logger.info(
#             f"send_meeting_notice: sent '{notice_type}' notice for meeting "
#             f"{meeting_id} to {len(to_emails)} recipients."
#         )
#     except Exception as exc:
#         logger.error(f"send_meeting_notice: email send failed – {exc}")
#         raise self.retry(exc=exc)

#     # Mark as sent
#     if schedule:
#         schedule.is_sent = True
#         schedule.save(update_fields=["is_sent"])
# ###second comment end


##first comment
# from celery import shared_task
# from django.core.mail import send_mail
# from django.conf import settings
# from django.utils import timezone
# from accounts.models import User
# from .models import MeetingSchedule
# import logging
# import pytz
# from datetime import datetime

# logger = logging.getLogger(__name__)


# @shared_task
# def check_meeting_reminders():
#     """
#     Periodically checks for upcoming meetings and sends reminder emails
#     based on 1440 minutes (24hr) and 10 minutes before the meeting.
#     """
#     ny_tz = pytz.timezone('America/New_York')
#     current_time = timezone.now().astimezone(ny_tz)

#     meetings = MeetingSchedule.objects.filter(
#         is_expired=False,
#         date__gte=current_time.date()
#     )

#     reminder_1440_count = 0
#     reminder_10_count = 0

#     for meeting in meetings:
#         try:
#             if not meeting.datetime_combined:
#                 continue

#             # 1440-minute (24hr) reminder
#             if (
#                 meeting.reminder_24hr_time and
#                 meeting.reminder_24hr_time <= current_time < meeting.datetime_combined and
#                 not meeting.reminder_24hr_sent
#             ):
#                 send_meeting_reminder_email.delay(meeting.id, 1440)
#                 meeting.reminder_24hr_sent = True
#                 meeting.save()
#                 reminder_1440_count += 1

#             # 10-minute reminder
#             if (
#                 meeting.reminder_10min_time and
#                 meeting.reminder_10min_time <= current_time < meeting.datetime_combined and
#                 not meeting.reminder_10min_sent
#             ):
#                 send_meeting_reminder_email.delay(meeting.id, 10)
#                 meeting.reminder_10min_sent = True
#                 meeting.save()
#                 reminder_10_count += 1

#         except Exception as e:
#             logger.error(f"Error checking reminders for meeting {meeting.id}: {e}")

#     logger.info(f"Total 1440-minute reminders: {reminder_1440_count}, 10-minute reminders: {reminder_10_count}")
#     return f"{reminder_1440_count} (1440min) and {reminder_10_count} (10min) reminders sent."


# @shared_task
# def send_meeting_reminder_email(meeting_id, reminder_minutes):
#     """
#     Sends reminder emails to all active users for a specific meeting,
#     reminder_minutes: 10 or 1440
#     """
#     try:
#         meeting = MeetingSchedule.objects.get(id=meeting_id)
#         users = User.objects.filter(is_active=True).exclude(email__isnull=True).exclude(email__exact='')
#         email_sent_count = 0

#         for user in users:
#             send_individual_reminder.delay(user.id, meeting.id, reminder_minutes)
#             email_sent_count += 1

#         logger.info(f"{reminder_minutes} min reminder scheduled for {email_sent_count} users for meeting {meeting.id}")
#         return f"{email_sent_count} reminders ({reminder_minutes} min) scheduled."

#     except MeetingSchedule.DoesNotExist:
#         logger.error(f"Meeting with ID {meeting_id} not found.")
#         return "Meeting not found."


# @shared_task
# def send_individual_reminder(user_id, meeting_id, reminder_minutes):
#     """
#     Sends a personalized email reminder to a user.
#     Reminder time in minutes (10 or 1440)
#     """
#     try:
#         user = User.objects.get(id=user_id)
#         meeting = MeetingSchedule.objects.get(id=meeting_id)

#         meeting_datetime = meeting.datetime_combined
#         formatted_time = meeting_datetime.strftime('%I:%M %p') if meeting_datetime else "N/A"
#         formatted_date = meeting.date.strftime('%d %B, %Y') if meeting.date else "N/A"

#         subject_prefix = "🔔 Final Reminder (10 min)" if reminder_minutes == 10 else "⏰ Reminder (24hr)"
#         subject = f"{subject_prefix}: {meeting.title}"

#         message = f"""
# Dear {user.get_full_name() or user.username},

# Assalamu Alaikum,

# This is a reminder for your upcoming meeting:

# 📅 Title: {meeting.title}
# 📆 Date: {formatted_date}
# ⏰ Start Time: {formatted_time}
# {f'📝 Description: {meeting.description}' if meeting.description else ''}

# {f'🔗 Meeting URL: {meeting.meeting_url}' if meeting.meeting_url else ''}
# {f'🔐 Password: {meeting.password}' if meeting.password else ''}

# This is your {'10-minute' if reminder_minutes == 10 else '24-hour'} reminder.

# Best regards,
# HFall Team
# ---
# Automated Email. Please do not reply.
#         """

#         send_mail(
#             subject,
#             message,
#             settings.DEFAULT_FROM_EMAIL,
#             [user.email],
#             fail_silently=False,
#         )

#         logger.info(f"Sent {reminder_minutes}-min reminder to {user.email} for meeting {meeting.id}")
#         return f"Email sent to {user.email}"

#     except Exception as e:
#         logger.error(f"Error sending {reminder_minutes}-min reminder to user {user_id}: {e}")
#         return f"Error: {e}"
