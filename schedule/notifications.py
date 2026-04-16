"""
notifications.py
────────────────
Schedule or cancel Celery-eta tasks for meeting email notices.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from celery import current_app
from django.utils import timezone

from .models import MeetingEmailSchedule

# Maps notice_type key → how far before the meeting to send it
NOTICE_OFFSETS: dict[str, timedelta] = {
    "3w":  timedelta(weeks=3),
    "2w":  timedelta(weeks=2),
    "1w":  timedelta(weeks=1),
    "1d":  timedelta(days=1),
    "10m": timedelta(minutes=10),
}


def _meeting_start_dt(meeting) -> datetime:
    import pytz
    naive = datetime.combine(meeting.date, meeting.start_time)
    ny_tz = pytz.timezone('America/New_York')
    return ny_tz.localize(naive)


# ── Public helpers ─────────────────────────────────────────────────────────

def cancel_meeting_notifications(meeting) -> None:
    """Revoke all pending Celery tasks and delete schedule rows for *meeting*."""
    qs = MeetingEmailSchedule.objects.filter(meeting=meeting)
    for row in qs:
        if row.task_id:
            try:
                current_app.control.revoke(row.task_id, terminate=False)
            except Exception:
                pass
    qs.delete()


def schedule_meeting_notifications(meeting) -> None:
    """
    Create (or update) MeetingEmailSchedule rows and Celery-eta tasks
    based on the notice flags on *meeting*.

    • If ``enable_all_email_notification`` is False every existing task is
      cancelled and all rows deleted.
    • Only notice types whose flag is True AND whose ETA is still in the
      future are scheduled.
    """
    # Import here to avoid circular import at module load time
    from .tasks import send_meeting_notice  # noqa: F401 – used via apply_async

    if not meeting.enable_all_email_notification:
        cancel_meeting_notifications(meeting)
        return

    # Which notice types are requested?
    selected: list[str] = []
    if meeting.notice_3_weeks: selected.append("3w")
    if meeting.notice_2_weeks: selected.append("2w")
    if meeting.notice_1_week:  selected.append("1w")
    if meeting.notice_1_day:   selected.append("1d")
    if meeting.notice_10_min:  selected.append("10m")

    # Cancel & remove rows for notice types that were de-selected
    existing: dict[str, MeetingEmailSchedule] = {
        row.notice_type: row
        for row in MeetingEmailSchedule.objects.filter(meeting=meeting)
    }
    for notice_type, row in existing.items():
        if notice_type not in selected:
            if row.task_id:
                try:
                    current_app.control.revoke(row.task_id, terminate=False)
                except Exception:
                    pass
            row.delete()

    start_dt = _meeting_start_dt(meeting)
    now      = timezone.now()

    for notice_type in selected:
        eta = start_dt - NOTICE_OFFSETS[notice_type]

        if eta <= now:
            # Past ETA – skip
            continue

        row, created = MeetingEmailSchedule.objects.get_or_create(
            meeting=meeting,
            notice_type=notice_type,
            defaults={"scheduled_for": eta},
        )

        # If ETA changed (meeting was edited) revoke the old task
        if not created and row.task_id and row.scheduled_for != eta:
            try:
                current_app.control.revoke(row.task_id, terminate=False)
            except Exception:
                pass

        row.scheduled_for = eta

        # Schedule the Celery task
        from .tasks import send_meeting_notice as _task
        result = _task.apply_async(args=[meeting.id, notice_type], eta=eta)

        row.task_id = result.id
        row.save(update_fields=["scheduled_for", "task_id"])