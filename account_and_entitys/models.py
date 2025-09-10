from django.db import models
# Removed encrypted fields import - using standard Django fields now

class XX_Account(models.Model):
    """Model representing ADJD accounts"""
    account = models.CharField(max_length=50, unique=False)
    parent = models.CharField(max_length=50, null=True, blank=True)  # Changed from EncryptedCharField
    alias_default = models.CharField(max_length=255, null=True, blank=True)  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.account)

    class Meta:
        db_table = 'XX_ACCOUNT_XX'

class XX_Entity(models.Model):
    """Model representing ADJD entities"""
    entity = models.CharField(max_length=50, unique=False)
    parent = models.CharField(max_length=50, null=True, blank=True)  # Changed from EncryptedCharField
    alias_default = models.CharField(max_length=255, null=True, blank=True)  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.entity)

    class Meta:
        db_table = 'XX_ENTITY_XX'


class XX_Project(models.Model):
    """Model representing ADJD entities"""
    project = models.CharField(max_length=50, unique=False)
    parent = models.CharField(
        max_length=50, null=True, blank=True
    )  # Changed from EncryptedCharField
    alias_default = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.project)

    class Meta:
        db_table = "XX_PROJECT_XX"


class XX_PivotFund(models.Model):
    """Model representing ADJD pivot funds"""
    entity = models.CharField(max_length=50)
    account = models.CharField(max_length=50)
    project = models.CharField(max_length=50, null=True, blank=True)
    year = models.IntegerField()
    actual = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)  # Changed from EncryptedCharField to DecimalField
    fund = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)  # Changed from EncryptedCharField to DecimalField
    budget = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)  # Changed from EncryptedCharField to DecimalField
    encumbrance = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)  # Changed from EncryptedCharField to DecimalField


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['entity', 'account', 'project', 'year'],
                name='unique_entity_account_year'
            )
        ]
        db_table = 'XX_PIVOTFUND_XX'

class XX_TransactionAudit(models.Model):
    """Model representing ADJD transaction audit records"""
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=50, null=True, blank=True)
    transfer_id = models.IntegerField(null=True, blank=True)
    transcation_code = models.CharField(max_length=50, null=True, blank=True)
    cost_center_code = models.CharField(max_length=50, null=True, blank=True)
    account_code = models.CharField(max_length=50, null=True, blank=True)
    project_code = models.CharField(max_length=50, null=True, blank=True)
    def __str__(self):
        return f"Audit {self.id}: {self.transcation_code}"

    class Meta:
        db_table = 'XX_TRANSACTION_AUDIT_XX'

class XX_ACCOUNT_ENTITY_LIMIT(models.Model):
    """Model representing ADJD account entity limits"""
    id = models.AutoField(primary_key=True)
    account_id = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50)
    project_id = models.CharField(max_length=50, null=True, blank=True)
    is_transer_allowed_for_source = models.CharField(max_length=255,null=True, blank=True)  # Changed from EncryptedBooleanField
    is_transer_allowed_for_target = models.CharField(max_length=255,null=True, blank=True)  # Changed from EncryptedBooleanField
    is_transer_allowed = models.CharField(max_length=255,null=True, blank=True)  # Changed from EncryptedBooleanField
    source_count = models.IntegerField(null=True, blank=True)  # Changed from EncryptedIntegerField
    target_count = models.IntegerField(null=True, blank=True)  # Changed from EncryptedIntegerField

    def __str__(self):
        return f"Account Entity Limit {self.id}"

    class Meta:
        db_table = 'XX_ACCOUNT_ENTITY_LIMIT_XX'
        unique_together = ('account_id', 'entity_id')


class XX_BalanceReport(models.Model):
    """Model representing balance report data from report.xlsx"""
    id = models.AutoField(primary_key=True)
    control_budget_name = models.CharField(max_length=100, null=True, blank=True, help_text="Control Budget Name")
    ledger_name = models.CharField(max_length=100, null=True, blank=True, help_text="Ledger Name")
    as_of_period = models.CharField(max_length=20, null=True, blank=True, help_text="As of Period (e.g., Sep-25)")
    segment1 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 1 (Cost Center)")
    segment2 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 2 (Account)")
    segment3 = models.CharField(max_length=50, null=True, blank=True, help_text="Segment 3 (Project)")
    encumbrance_ytd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="Encumbrance Year to Date")
    other_ytd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="Other Year to Date")
    actual_ytd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="Actual Year to Date")
    funds_available_asof = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="Funds Available As Of")
    budget_ytd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, help_text="Budget Year to Date")
    
    # Additional metadata fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Balance Report: {self.control_budget_name} - {self.segment1}/{self.segment2}/{self.segment3}"
    
    class Meta:
        db_table = 'XX_BALANCE_REPORT_XX'
        verbose_name = "Balance Report"
        verbose_name_plural = "Balance Reports"
        indexes = [
            models.Index(fields=['control_budget_name', 'as_of_period']),
            models.Index(fields=['segment1', 'segment2', 'segment3']),
            models.Index(fields=['as_of_period']),
        ]



