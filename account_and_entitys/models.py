from django.db import models
# Removed encrypted fields import - using standard Django fields now

class XX_Account(models.Model):
    """Model representing ADJD accounts"""
    account = models.CharField(max_length=50, unique=True)
    parent = models.CharField(max_length=50, null=True, blank=True)  # Changed from EncryptedCharField
    alias_default = models.CharField(max_length=255, null=True, blank=True)  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.account)

    class Meta:
        db_table = 'XX_Account_XX'

class XX_Entity(models.Model):
    """Model representing ADJD entities"""
    entity = models.CharField(max_length=50, unique=True)
    parent = models.CharField(max_length=50, null=True, blank=True)  # Changed from EncryptedCharField
    alias_default = models.CharField(max_length=255, null=True, blank=True)  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.entity)

    class Meta:
        db_table = 'XX_Entity_XX'


class XX_Project(models.Model):
    """Model representing ADJD entities"""
    project = models.CharField(max_length=50, unique=True)
    parent = models.CharField(
        max_length=50, null=True, blank=True
    )  # Changed from EncryptedCharField
    alias_default = models.CharField(
        max_length=255, null=True, blank=True
    )  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.entity)

    class Meta:
        db_table = "XX_Project_XX"


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
        db_table = 'XX_PivotFund_XX'

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
