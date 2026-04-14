from celery import shared_task
from .tasks import publish_due_polls_and_notify

@shared_task
def poll_publish_and_notify_task():
    publish_due_polls_and_notify()