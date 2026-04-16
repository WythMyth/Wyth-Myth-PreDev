import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_poll_invitation_email(*, poll, recipients):
    """
    recipients: list[str] emails
    """
    if not recipients:
        return 0

    subject = f"New Poll: {poll.title}"
    from_email = settings.DEFAULT_FROM_EMAIL

    poll_url = f"{settings.SITE_URL}/dashboard/polls/{poll.pk}/vote/"
    context = {
        "poll": poll,
        "poll_url": poll_url,
        "site_url": settings.SITE_URL,
    }

    text_body = render_to_string("emails/poll_invite.txt", context)
    html_body = render_to_string("emails/poll_invite.html", context)

    logger.warning("=" * 60)
    logger.warning("POLL EMAIL NOTIFICATION")
    logger.warning(f"Poll: {poll.title}")
    logger.warning(f"Recipients ({len(recipients)}): {recipients}")
    logger.warning("=" * 60)

    # Send in batches to avoid huge To list
    sent = 0
    chunk_size = 80
    for i in range(0, len(recipients), chunk_size):
        batch = recipients[i : i + chunk_size]

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=[],  # keep To empty
            bcc=batch,  # ✅ privacy safe
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send()
        sent += len(batch)

    return sent
