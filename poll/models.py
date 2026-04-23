from django.db import models
from django.utils import timezone

from django.conf import settings
from schedule.models import Tag


class Poll(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_UPCOMING = "upcoming"
    STATUS_PUBLISHED = "published"
    VISIBILITY_SHOW = "show"
    VISIBILITY_ANON = "anonymous"
    VISIBILITY_CHOICES = [
        (VISIBILITY_SHOW, "Show"),
        (VISIBILITY_ANON, "Anonymous"),
    ]
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_UPCOMING, "Upcoming"),
        (STATUS_PUBLISHED, "Published"),
    ]

    title = models.CharField(max_length=255)
    message_need_to_be_send = models.TextField(blank=True)

    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )

    tags = models.ManyToManyField(Tag, blank=True, related_name="polls")
    vote_visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_ANON,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="polls_created",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def can_user_access(self, user):
        if not user.is_authenticated:
            return False
        if hasattr(user, "tags"):
            return self.tags.filter(
                id__in=user.tags.values_list("id", flat=True)
            ).exists()
        return False


class Question(models.Model):
    TYPE_SINGLE = "single"
    TYPE_MULTI = "multi"

    TYPE_CHOICES = [
        (TYPE_SINGLE, "Single Choice"),
        (TYPE_MULTI, "Multiple Choice"),
    ]

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="questions")
    title = models.CharField(max_length=255)
    qtype = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_SINGLE)
    allow_other = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Choice(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="choices"
    )
    label = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.label


class PollResponse(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="responses")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="poll_responses",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("poll", "user")


class Vote(models.Model):
    response = models.ForeignKey(
        PollResponse, on_delete=models.CASCADE, related_name="votes"
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="votes"
    )
    choice = models.ForeignKey(
        Choice, on_delete=models.SET_NULL, null=True, blank=True, related_name="votes"
    )
    other_text = models.TextField(blank=True)
