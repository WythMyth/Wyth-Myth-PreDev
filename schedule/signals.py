"""
signals.py
──────────
Automatically cancel queued email-notice tasks when a MeetingSchedule
instance is about to be deleted.
"""
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import MeetingSchedule
from .notifications import cancel_meeting_notifications


@receiver(pre_delete, sender=MeetingSchedule)
def meeting_pre_delete(sender, instance, **kwargs):
    """Revoke all pending Celery tasks tied to this meeting before deletion."""
    cancel_meeting_notifications(instance)