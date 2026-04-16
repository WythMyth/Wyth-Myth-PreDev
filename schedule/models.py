import uuid
from datetime import datetime, timedelta

import pytz
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class AbstractField(models.Model):
    is_active = models.BooleanField(default=True)
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Meeting(AbstractField):
    meeting_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='meeting_holder', null=True
    )
    title = models.CharField(max_length=255, null=True)
    description = models.TextField(null=True, blank=True)
    date = models.DateField(null=True)
    start_time = models.CharField(null=True, blank=True, max_length=100)
    end_time = models.CharField(null=True, blank=True, max_length=100)
    meeting_url = models.URLField(null=True)
    password = models.CharField(max_length=50, null=True, blank=True)
    is_expired = models.BooleanField(default=False)
    is_sms = models.BooleanField(default=False, null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title', 'date', 'start_time']


class MeetingSchedule(AbstractField):
    # ── Recurring / Series fields ──────────────────────────────────────────
    series_id = models.UUIDField(
        default=uuid.uuid4,
        db_index=True,
        help_text="All occurrences of a recurring meeting share the same series_id.",
    )
    occurrence_index = models.PositiveIntegerField(
        default=1,
        help_text="1-based position of this occurrence within the series.",
    )
    is_recurring = models.BooleanField(
        default=False,
        help_text="True only on the *first* occurrence (the series root).",
    )

    # ── Core fields ────────────────────────────────────────────────────────
    meeting_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='meeting_schedule_holder',
        null=True,
    )
    guests = models.ManyToManyField(
        "schedule.Tag",
        blank=True,
        related_name="meetings",
        help_text="Users who have any of these tags will receive email.",
    )
    title = models.CharField(max_length=255, null=True)
    description = models.TextField(null=True, blank=True)
    date = models.DateField(null=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    meeting_url = models.URLField(null=True)
    password = models.CharField(max_length=50, null=True, blank=True)
    is_expired = models.BooleanField(default=False)
    is_sms = models.BooleanField(default=False, null=True, blank=True)

    # ── Old reminder flags (kept for backward-compat) ──────────────────────
    reminder_10min_sent = models.BooleanField(
        default=False, help_text="Email sent 10 minutes before meeting"
    )
    reminder_24hr_sent = models.BooleanField(
        default=False, help_text="Email sent 24 hours before meeting"
    )

    # ── New email-notification notice toggles ──────────────────────────────
    enable_all_email_notification = models.BooleanField(
        default=False,
        help_text="Master switch – must be ON for any notice to be sent.",
    )
    notice_3_weeks = models.BooleanField(default=False)
    notice_2_weeks = models.BooleanField(default=False)
    notice_1_week  = models.BooleanField(default=False)
    notice_1_day   = models.BooleanField(default=False)
    notice_10_min  = models.BooleanField(default=False)

    def __str__(self):
        return self.title or "Untitled Meeting"

    # ── Helpers ────────────────────────────────────────────────────────────
    @property
    def datetime_combined(self):
        if self.date and self.start_time:
            naive_datetime = datetime.combine(self.date, self.start_time)
            ny_tz = pytz.timezone('America/New_York')
            if timezone.is_naive(naive_datetime):
                return ny_tz.localize(naive_datetime)
            return naive_datetime
        return None

    @property
    def reminder_10min_time(self):
        if self.datetime_combined:
            return self.datetime_combined - timedelta(minutes=10)
        return None

    @property
    def reminder_24hr_time(self):
        if self.datetime_combined:
            return self.datetime_combined - timedelta(minutes=1440)
        return None

    class Meta:
        ordering = ['title', 'date', 'start_time']


# ---------------------------------------------------------------------------
# Email-schedule tracking (one row per meeting × notice_type)
# ---------------------------------------------------------------------------
class MeetingEmailSchedule(models.Model):
    NOTICE_3W = "3w"
    NOTICE_2W = "2w"
    NOTICE_1W = "1w"
    NOTICE_1D = "1d"
    NOTICE_10M = "10m"
    NOTICE_CHOICES = [
        (NOTICE_3W, "3 Weeks"),
        (NOTICE_2W, "2 Weeks"),
        (NOTICE_1W, "1 Week"),
        (NOTICE_1D, "1 Day"),
        (NOTICE_10M, "10 Minutes"),
    ]

    meeting = models.ForeignKey(
        MeetingSchedule,
        on_delete=models.CASCADE,
        related_name="email_schedules",
    )
    notice_type = models.CharField(max_length=10, choices=NOTICE_CHOICES)
    scheduled_for = models.DateTimeField()
    task_id = models.CharField(max_length=255, blank=True, null=True)
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("meeting", "notice_type")

    def __str__(self):
        return f"{self.meeting} – {self.notice_type}"


# ---------------------------------------------------------------------------
# Class recording (unchanged)
# ---------------------------------------------------------------------------
class ClassRecording(AbstractField):
    meeting = models.ForeignKey(
        MeetingSchedule, on_delete=models.PROTECT, related_name='recording'
    )
    recording_url = models.URLField(null=True)
    description = models.CharField(max_length=1000, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.meeting.is_expired is False:
            self.meeting.is_expired = True
            self.meeting.save()
        return super().save(*args, **kwargs)

class Tag(models.Model):
    name = models.CharField(max_length=80, unique=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return self.name




# from django.db import models
# from accounts.models import User
# from django.utils import timezone
# import pytz
# from datetime import datetime, timedelta

# class AbstractField(models.Model):
#     is_active = models.BooleanField(default=True)
#     create_at = models.DateTimeField(auto_now_add=True)
#     update_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         abstract = True
# class Meeting(AbstractField):
#     meeting_user = models.ForeignKey(
#         User, on_delete=models.CASCADE, related_name='meeting_holder', null=True
#     )
#     title = models.CharField(max_length=255, null=True)
#     description = models.TextField(null=True, blank=True)
#     date = models.DateField(null=True)
#     start_time = models.CharField(null=True, blank=True, max_length=100)
#     end_time = models.CharField(null=True, blank=True, max_length=100)
#     meeting_url = models.URLField(null=True)
#     password = models.CharField(max_length=50, null=True, blank=True)
#     is_expired = models.BooleanField(default=False)
#     is_sms = models.BooleanField(default=False, null=True, blank=True)

#     def __str__(self):
#         return self.title
    
#     class Meta:
#         ordering = ['title', 'date', 'start_time']
        
# class MeetingSchedule(AbstractField):
#     meeting_user = models.ForeignKey(
#         User, on_delete=models.CASCADE, related_name='meeting_schedule_holder', null=True
#     )
#     title = models.CharField(max_length=255, null=True)
#     description = models.TextField(null=True, blank=True)
#     date = models.DateField(null=True)
#     start_time = models.TimeField(null=True, blank=True)
#     end_time = models.TimeField(null=True, blank=True)
#     meeting_url = models.URLField(null=True)
#     password = models.CharField(max_length=50, null=True, blank=True)
#     is_expired = models.BooleanField(default=False)
#     is_sms = models.BooleanField(default=False, null=True, blank=True)
    
 
#     reminder_10min_sent = models.BooleanField(default=False, help_text="Email sent 10 minutes before meeting")
#     reminder_24hr_sent = models.BooleanField(default=False, help_text="Email sent 24 hours before meeting")
    
#     def __str__(self):
#         return self.title or "Untitled Meeting"
    
#     @property
#     def datetime_combined(self):
       
#         if self.date and self.start_time:
            
#             naive_datetime = datetime.combine(self.date, self.start_time)
            
#             dhaka_tz = pytz.timezone('America/New_York')
            
#             if timezone.is_naive(naive_datetime):
                
#                 localized_datetime = dhaka_tz.localize(naive_datetime)
#                 return localized_datetime
#             return naive_datetime
#         return None
    
#     @property
#     def reminder_10min_time(self):
#         """
#         Returns datetime 10 minutes before meeting start time.
#         """
#         if self.datetime_combined:
#             return self.datetime_combined - timedelta(minutes=10)
#         return None

#     @property
#     def reminder_24hr_time(self):
#         """
#         Returns datetime 24 hours before meeting start time.
#         """
#         if self.datetime_combined:
#             return self.datetime_combined - timedelta(minutes=1440)
#         return None

    
#     class Meta:
#         ordering = ['title', 'date', 'start_time']
# class ClassRecording(AbstractField):
#     meeting = models.ForeignKey(
#         MeetingSchedule, on_delete=models.PROTECT, related_name='recording'
#     )
#     recording_url = models.URLField(null=True)
#     description = models.CharField(max_length=1000, null=True, blank=True)

#     def save(self):
#         meeting = self.meeting.is_expired
#         if meeting is False:
#             self.meeting.is_expired = True
#         return super().save()
