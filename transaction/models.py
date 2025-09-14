from django.db import models
from budget_management.models import xx_BudgetTransfer

# Removed encrypted fields import - using standard Django fields now


class xx_TransactionTransfer(models.Model):
    """Model for ADJD transaction transfers"""

    transfer_id = models.AutoField(primary_key=True)
    approved_budget = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Changed from EncryptedTextField to DecimalField
    available_budget = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Changed from EncryptedTextField to DecimalField
    from_center = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Changed from TextField to DecimalField
    to_center = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Changed from TextField to DecimalField
    transaction = models.ForeignKey(
        xx_BudgetTransfer,
        on_delete=models.CASCADE,
        db_column="transaction_id",
        null=True,
        blank=True,
        related_name="transfers",
    )
    reason = models.TextField(
        null=True, blank=True
    )  # Keep as TextField but avoid in complex queries
    account_code = models.IntegerField(null=True, blank=True)
    account_name = models.TextField(
        null=True, blank=True
    )  # Keep as TextField but avoid in complex queries
    project_code = models.TextField(null=True, blank=True)
    project_name = models.TextField(
        null=True, blank=True
    )  # Keep as TextField but avoid in complex queries
    cost_center_code = models.IntegerField(null=True, blank=True)
    cost_center_name = models.TextField(
        null=True, blank=True
    )  # Keep as TextField but avoid in complex queries
    done = models.IntegerField(default=1)
    encumbrance = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Changed from EncryptedTextField to DecimalField
    actual = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )  # Changed from EncryptedTextField to DecimalField
    # Additional file field for attachments
    file = models.FileField(upload_to="transfers/", null=True, blank=True)

    class Meta:
        db_table = "XX_TRANSACTION_TRANSFER_XX"

    def __str__(self):
        return f"ADJD Transfer {self.transfer_id}"
