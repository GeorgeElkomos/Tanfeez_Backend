# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from approvals.managers import ApprovalManager
from approvals.models import ApprovalWorkflowInstance


@receiver(post_save)
def start_workflow_on_submit(sender, instance, created, **kwargs):
    """
    When a BudgetTransfer is submitted, start its workflow instance.
    """
    # Lazy-load the BudgetTransfer model to avoid import-time circular imports
    BudgetTransfer = apps.get_model("budget_management", "xx_BudgetTransfer")

    # Only handle events for the BudgetTransfer model
    if sender != BudgetTransfer and not isinstance(instance, BudgetTransfer):
        return

    if not created and getattr(instance, "status", None) == "submitted":
        instance.status = "pending"
        instance.save(update_fields=["status"])
        ApprovalManager.start_workflow(
            transfer_type=instance.type.lower(), budget_transfer=instance
        )
