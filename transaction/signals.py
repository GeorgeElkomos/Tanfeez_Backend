# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from approvals.managers import ApprovalManager
from approvals.models import ApprovalWorkflowInstance
from .models import xx_BudgetTransfer


@receiver(post_save, sender=xx_BudgetTransfer)
def start_workflow_on_submit(sender, instance, created, **kwargs):
    """
    When a BudgetTransfer is submitted, start its workflow instance.
    """
    if not created and instance.status == "submitted":
        instance.status = "pending"
        instance.save(update_fields=["status"])
        ApprovalManager.start_workflow(
            transfer_type=instance.type.lower(), budget_transfer=instance
        )
