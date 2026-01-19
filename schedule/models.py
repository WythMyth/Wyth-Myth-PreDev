from django.db import models
from accounts.models import User
from django.utils import timezone
import pytz
from datetime import datetime, timedelta

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
    meeting_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='meeting_schedule_holder', null=True
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
    
 
    reminder_10min_sent = models.BooleanField(default=False, help_text="Email sent 10 minutes before meeting")
    reminder_24hr_sent = models.BooleanField(default=False, help_text="Email sent 24 hours before meeting")
    
    def __str__(self):
        return self.title or "Untitled Meeting"
    
    @property
    def datetime_combined(self):
       
        if self.date and self.start_time:
            
            naive_datetime = datetime.combine(self.date, self.start_time)
            
            dhaka_tz = pytz.timezone('America/New_York')
            
            if timezone.is_naive(naive_datetime):
                
                localized_datetime = dhaka_tz.localize(naive_datetime)
                return localized_datetime
            return naive_datetime
        return None
    
    @property
    def reminder_10min_time(self):
        """
        Returns datetime 10 minutes before meeting start time.
        """
        if self.datetime_combined:
            return self.datetime_combined - timedelta(minutes=10)
        return None

    @property
    def reminder_24hr_time(self):
        """
        Returns datetime 24 hours before meeting start time.
        """
        if self.datetime_combined:
            return self.datetime_combined - timedelta(minutes=1440)
        return None

    
    class Meta:
        ordering = ['title', 'date', 'start_time']
class ClassRecording(AbstractField):
    meeting = models.ForeignKey(
        MeetingSchedule, on_delete=models.PROTECT, related_name='recording'
    )
    recording_url = models.URLField(null=True)
    description = models.CharField(max_length=1000, null=True, blank=True)

    def save(self):
        meeting = self.meeting.is_expired
        if meeting is False:
            self.meeting.is_expired = True
        return super().save()
