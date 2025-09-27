from django.db import models
from django.utils import timezone
from datetime import timedelta
from budget_management.models import xx_BudgetTransfer


# Create your models here.
class Chat(models.Model):
    user_from = models.ForeignKey(
        "user_management.xx_User", on_delete=models.CASCADE, related_name="chats_sent"
    )
    user_to = models.ForeignKey(
        "user_management.xx_User",
        on_delete=models.CASCADE,
        related_name="chats_received",
    )
    transaction = models.ForeignKey(
        xx_BudgetTransfer,
        on_delete=models.CASCADE,
        related_name="chats",
    )
    message = models.TextField(blank=False, null=False, max_length=5000)
    original_message = models.TextField(null=True, blank=True, max_length=5000)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    edit_history = models.JSONField(
        default=list, blank=True, help_text="List of previous versions with timestamps"
    )
    seen = models.BooleanField(
        default=False, help_text="Whether the message has been seen by the recipient"
    )
    seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["user_from", "user_to"]),
            models.Index(fields=["transaction"]),
        ]
        ordering = ["-timestamp"]

    @property
    def can_edit(self):
        """Check if the message is still within the 15-minute edit window"""
        return timezone.now() - self.timestamp < timedelta(minutes=15)

    def __str__(self):
        return f"{self.user_from}: {self.message[:20]}..."
