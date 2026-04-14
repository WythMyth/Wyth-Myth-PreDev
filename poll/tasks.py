import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from .emails import send_poll_invitation_email
from .models import Poll

logger = logging.getLogger(__name__)


@shared_task
def send_poll_notification_task(poll_id):
    """
    Scheduled with eta=poll.start_at so it fires at exactly the right time.
    Publishes the poll (if not yet published) and sends the invitation email
    once to all tagged users.
    """
    now = timezone.now()
    User = get_user_model()

    try:
        poll = Poll.objects.prefetch_related("tags").get(pk=poll_id)
    except Poll.DoesNotExist:
        logger.warning(
            f"send_poll_notification_task: Poll {poll_id} not found, skipping."
        )
        return

    logger.warning("=" * 60)
    logger.warning(f"POLL NOTIFICATION TASK — poll_id={poll_id} title='{poll.title}'")
    logger.warning(f"Fired at: {now}")

    # 1) Publish if not already published
    if poll.status in (Poll.STATUS_DRAFT, Poll.STATUS_UPCOMING):
        poll.status = Poll.STATUS_PUBLISHED
        poll.published_at = now
        poll.save(update_fields=["status", "published_at"])
        logger.warning(f"Published poll: {poll.title}")

    # 2) Send notification only once
    if poll.notification_sent_at is not None:
        logger.warning(f"Poll '{poll.title}' already notified, skipping email.")
        return

    tag_ids = list(poll.tags.values_list("id", flat=True))
    logger.warning(f"Poll '{poll.title}' tag_ids: {tag_ids}")

    if not tag_ids:
        logger.warning(f"Poll '{poll.title}' has no tags, skipping email.")
        poll.notification_sent_at = now
        poll.save(update_fields=["notification_sent_at"])
        return

    users_qs = User.objects.filter(is_active=True, tags__in=tag_ids).distinct()
    recipients = list(
        users_qs.exclude(email__isnull=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )
    logger.warning(f"Poll '{poll.title}' recipients: {recipients}")

    send_poll_invitation_email(poll=poll, recipients=recipients)

    poll.notification_sent_at = now
    poll.save(update_fields=["notification_sent_at"])

    logger.warning(f"POLL NOTIFICATION SENT for '{poll.title}'")
    logger.warning("=" * 60)
