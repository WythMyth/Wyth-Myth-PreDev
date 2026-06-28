from django.conf import settings
from django.db import models


class AIChatSession(models.Model):
    CHAT_TYPE_CHOICES = (
        ("user_finance", "User Finance Chat"),
        ("finance_review", "Finance Review"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_chat_sessions",
    )

    chat_type = models.CharField(
        max_length=30,
        choices=CHAT_TYPE_CHOICES,
        default="user_finance",
    )

    title = models.CharField(
        max_length=255,
        default="AI Finance Assistant",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} - {self.title}"


class AIChatMessage(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    )

    session = models.ForeignKey(
        AIChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
    )

    content = models.TextField()

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.session_id} - {self.role}"


class AIPredictionLog(models.Model):
    """
    Optional log for finance/admin AI predictions.
    No financial action happens here.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_prediction_logs",
    )

    prediction_type = models.CharField(max_length=100)
    input_snapshot = models.JSONField(default=dict, blank=True)
    ai_response = models.TextField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_ai_prediction_logs",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.prediction_type} - {self.created_at}"