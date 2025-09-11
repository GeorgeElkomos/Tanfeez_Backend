"""
Django signals for xx_BudgetTransfer model
Automatically execute functions when budget transfer changes occur
"""

from django.db.models.signals import post_save, pre_save, post_delete, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from approvals.managers import ApprovalManager
from ..models import xx_BudgetTransfer
from user_management.models import xx_notification
import logging
from budget_transfer.global_function.dashbaord import dashboard_smart, dashboard_normal

# Configure logging for budget transfer signals
logger = logging.getLogger("budget_transfer_signals")

# ============================================================================
# xx_BudgetTransfer Signals
# ============================================================================


@receiver(post_save, sender=xx_BudgetTransfer)
def budget_transfer_post_save(sender, instance, created, **kwargs):
    """
    Function executed AFTER saving xx_BudgetTransfer
    Use this for notifications, related updates, or post-processing
    """
    try:
        # Run dashboard function for ALL saves (create AND update)
        if instance.status == "approved":
            print("approved enterd")
            dashboard_smart()
        # elif instance.status == "pending":
        print("pending enterd")
        dashboard_normal()

        if created:
            logger.info(
                f"New BudgetTransfer created: {instance.transaction_id} - Dashboard updated"
            )
        else:
            logger.info(
                f"BudgetTransfer updated: {instance.transaction_id} - Dashboard updated"
            )

    except Exception as e:
        logger.error(f"Error in budget_transfer_post_save: {str(e)}")


@receiver(post_delete, sender=xx_BudgetTransfer)
def budget_transfer_post_delete(sender, instance, **kwargs):
    """
    Function executed AFTER deleting xx_BudgetTransfer
    Use this for cleanup, notifications, or post-deletion processing
    """
    try:
        dashboard_smart()

        logger.info(
            f"Dashboard updated after deleting BudgetTransfer {instance.transaction_id}"
        )

    except Exception as e:
        logger.error(f"Error in budget_transfer_post_delete: {str(e)}")


print("📡 budget_transfer signals module loaded")  # DEBUG


@receiver(post_save, sender=xx_BudgetTransfer)
def create_workflow_instance(sender, instance, created, **kwargs):
    print(
        "🔥 post_save fired for transfer", instance.transaction_id, "created:", created
    )
    if created:
        ApprovalManager.create_instance(
            transfer_type=instance.type.upper(), budget_transfer=instance
        )
