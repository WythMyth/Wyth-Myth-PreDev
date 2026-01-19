from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from accounts.models import User
from .models import MeetingSchedule
import logging
import pytz
from datetime import datetime

logger = logging.getLogger(__name__)


@shared_task
def check_meeting_reminders():
    """
    Periodically checks for upcoming meetings and sends reminder emails
    based on 1440 minutes (24hr) and 10 minutes before the meeting.
    """
    ny_tz = pytz.timezone('America/New_York')
    current_time = timezone.now().astimezone(ny_tz)

    meetings = MeetingSchedule.objects.filter(
        is_expired=False,
        date__gte=current_time.date()
    )

    reminder_1440_count = 0
    reminder_10_count = 0

    for meeting in meetings:
        try:
            if not meeting.datetime_combined:
                continue

            # 1440-minute (24hr) reminder
            if (
                meeting.reminder_24hr_time and
                meeting.reminder_24hr_time <= current_time < meeting.datetime_combined and
                not meeting.reminder_24hr_sent
            ):
                send_meeting_reminder_email.delay(meeting.id, 1440)
                meeting.reminder_24hr_sent = True
                meeting.save()
                reminder_1440_count += 1

            # 10-minute reminder
            if (
                meeting.reminder_10min_time and
                meeting.reminder_10min_time <= current_time < meeting.datetime_combined and
                not meeting.reminder_10min_sent
            ):
                send_meeting_reminder_email.delay(meeting.id, 10)
                meeting.reminder_10min_sent = True
                meeting.save()
                reminder_10_count += 1

        except Exception as e:
            logger.error(f"Error checking reminders for meeting {meeting.id}: {e}")

    logger.info(f"Total 1440-minute reminders: {reminder_1440_count}, 10-minute reminders: {reminder_10_count}")
    return f"{reminder_1440_count} (1440min) and {reminder_10_count} (10min) reminders sent."


@shared_task
def send_meeting_reminder_email(meeting_id, reminder_minutes):
    """
    Sends reminder emails to all active users for a specific meeting,
    reminder_minutes: 10 or 1440
    """
    try:
        meeting = MeetingSchedule.objects.get(id=meeting_id)
        users = User.objects.filter(is_active=True).exclude(email__isnull=True).exclude(email__exact='')
        email_sent_count = 0

        for user in users:
            send_individual_reminder.delay(user.id, meeting.id, reminder_minutes)
            email_sent_count += 1

        logger.info(f"{reminder_minutes} min reminder scheduled for {email_sent_count} users for meeting {meeting.id}")
        return f"{email_sent_count} reminders ({reminder_minutes} min) scheduled."

    except MeetingSchedule.DoesNotExist:
        logger.error(f"Meeting with ID {meeting_id} not found.")
        return "Meeting not found."


@shared_task
def send_individual_reminder(user_id, meeting_id, reminder_minutes):
    """
    Sends a personalized email reminder to a user.
    Reminder time in minutes (10 or 1440)
    """
    try:
        user = User.objects.get(id=user_id)
        meeting = MeetingSchedule.objects.get(id=meeting_id)

        meeting_datetime = meeting.datetime_combined
        formatted_time = meeting_datetime.strftime('%I:%M %p') if meeting_datetime else "N/A"
        formatted_date = meeting.date.strftime('%d %B, %Y') if meeting.date else "N/A"

        subject_prefix = "🔔 Final Reminder (10 min)" if reminder_minutes == 10 else "⏰ Reminder (24hr)"
        subject = f"{subject_prefix}: {meeting.title}"

        message = f"""
Dear {user.get_full_name() or user.username},

Assalamu Alaikum,

This is a reminder for your upcoming meeting:

📅 Title: {meeting.title}
📆 Date: {formatted_date}
⏰ Start Time: {formatted_time}
{f'📝 Description: {meeting.description}' if meeting.description else ''}

{f'🔗 Meeting URL: {meeting.meeting_url}' if meeting.meeting_url else ''}
{f'🔐 Password: {meeting.password}' if meeting.password else ''}

This is your {'10-minute' if reminder_minutes == 10 else '24-hour'} reminder.

Best regards,  
HFall Team
---
Automated Email. Please do not reply.
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        logger.info(f"Sent {reminder_minutes}-min reminder to {user.email} for meeting {meeting.id}")
        return f"Email sent to {user.email}"

    except Exception as e:
        logger.error(f"Error sending {reminder_minutes}-min reminder to user {user_id}: {e}")
        return f"Error: {e}"






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
#     Periodically (every minute) checks for upcoming meetings that need reminder emails
#     """
#     # Get current time in New York timezone
#     ny_tz = pytz.timezone('America/New_York') 
#     current_time = timezone.now().astimezone(ny_tz)
    
#     logger.info(f"Current time (New York): {current_time}")
    
#     # Find meetings that haven't expired or sent reminders yet
#     meetings = MeetingSchedule.objects.filter(
#         is_expired=False,
#         reminder_sent=False,
#         date__gte=current_time.date()
#     )
    
#     reminder_count = 0
    
#     for meeting in meetings:
#         try:
#             meeting_datetime = meeting.datetime_combined
#             reminder_time = meeting.reminder_time
            
#             if meeting_datetime and reminder_time:
#                 logger.info(f"Checking meeting: {meeting.title}")
#                 logger.info(f"Meeting datetime: {meeting_datetime}")
#                 logger.info(f"Reminder time: {reminder_time}")
                
#                 # Send reminder only if current time is between reminder_time and meeting time
#                 if reminder_time <= current_time < meeting_datetime:
#                     send_meeting_reminder_email.delay(meeting.id)
#                     logger.info(f"Scheduled reminder for meeting: {meeting.title}")
#                     reminder_count += 1
                    
#         except Exception as e:
#             logger.error(f"Error processing meeting {meeting.id}: {e}")
    
#     logger.info(f"Total reminders scheduled: {reminder_count}")
#     return f"Checked meetings. {reminder_count} reminders scheduled."


# @shared_task
# def send_meeting_reminder_email(meeting_id):
#     """
#     Sends reminder emails to all active users for a specific meeting
#     """
#     try:
#         meeting = MeetingSchedule.objects.get(id=meeting_id)
        
#         if meeting.reminder_sent:
#             logger.info(f"Reminder already sent for meeting: {meeting.title}")
#             return "Reminder already sent."
        
#         users = User.objects.filter(is_active=True).exclude(email__isnull=True).exclude(email__exact='')
        
#         email_sent_count = 0
#         for user in users:
#             try:
#                 send_individual_reminder.delay(user.id, meeting.id)
#                 email_sent_count += 1
#             except Exception as e:
#                 logger.error(f"Error scheduling email for user {user.id}: {e}")
        
#         meeting.reminder_sent = True
#         meeting.save()
        
#         logger.info(f"Scheduled {email_sent_count} reminder emails for meeting: {meeting.title}")
#         return f"Scheduled {email_sent_count} reminder emails."
        
#     except MeetingSchedule.DoesNotExist:
#         logger.error(f"Meeting with ID {meeting_id} not found.")
#         return "Meeting not found."
#     except Exception as e:
#         logger.error(f"Unexpected error in send_meeting_reminder_email: {e}")
#         return f"Error: {e}"


# @shared_task
# def send_individual_reminder(user_id, meeting_id):
#     """
#     Sends a personalized reminder email to a single user
#     """
#     try:
#         user = User.objects.get(id=user_id)
#         meeting = MeetingSchedule.objects.get(id=meeting_id)
        
#         ny_tz = pytz.timezone('America/New_York')
#         meeting_datetime = meeting.datetime_combined
        
#         if meeting_datetime:
#             formatted_time = meeting_datetime.strftime('%I:%M %p')
#             formatted_date = meeting.date.strftime('%d %B, %Y')
#         else:
#             formatted_time = str(meeting.start_time) if meeting.start_time else "Time not specified"
#             formatted_date = str(meeting.date) if meeting.date else "Date not specified"
        
#         subject = f"🔔 Meeting Reminder: {meeting.title}"
        
#         message = f"""
# Dear {user.get_full_name() or user.username},

# Assalamu Alaikum!

# You have an important meeting scheduled to start in 10 minutes:

# 📅 Meeting: {meeting.title}
# 📆 Date: {formatted_date}
# ⏰ Time: {formatted_time}
# 🕒 End Time: {meeting.end_time.strftime('%I:%M %p') if meeting.end_time else 'Not specified'}

# {f'📝 Description: {meeting.description}' if meeting.description else ''}

# {f'🔗 Meeting Link: {meeting.meeting_url}' if meeting.meeting_url else ''}
# {f'🔐 Password: {meeting.password}' if meeting.password else ''}

# Please be on time.

# Best regards,  
# HFall Team

# ---
# This is an automated message. Please do not reply.
#         """
        
#         send_mail(
#             subject=subject,
#             message=message,
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[user.email],
#             fail_silently=False,
#         )
        
#         logger.info(f"Reminder email sent to {user.email} for meeting: {meeting.title}")
#         return f"Email sent to {user.email}"
        
#     except (User.DoesNotExist, MeetingSchedule.DoesNotExist) as e:
#         logger.error(f"Error sending reminder: {e}")
#         return f"Error: {e}"
#     except Exception as e:
#         logger.error(f"Unexpected error sending reminder: {e}")
#         return f"Error: {e}"
