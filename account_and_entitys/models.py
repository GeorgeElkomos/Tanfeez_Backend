from django.db import models
from transaction.models import xx_TransactionTransfer
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

class Project_Envelope(models.Model):
    """Model representing ADJD entities"""
    project = models.CharField(max_length=50, unique=False)
    envelope = models.DecimalField(max_digits=30, decimal_places=2)  # Changed from EncryptedCharField

    def __str__(self):
        return str(self.project)

    class Meta:
        db_table = "XX_PROJECT_ENVELOPE_XX"

class EnvelopeManager(models.Model):
    @staticmethod
    def Has_Envelope(project_code):
        try:
            envelope_record = Project_Envelope.objects.get(project=project_code)
            return True
        except Project_Envelope.DoesNotExist:
            return False

    @staticmethod
    def Get_Envelope(project_code):
        try:
            envelope_record = Project_Envelope.objects.get(project=project_code)
            return envelope_record.envelope
        except Project_Envelope.DoesNotExist:
            return 0
    
    @staticmethod
    def __get_project_parent_code(project_code):
        try:
            parent_project = XX_Project.objects.get(project=project_code)
            return parent_project.parent
        except XX_Project.DoesNotExist:
            return None

    @staticmethod
    def Get_First_Parent_Envelope(project_code):
        while project_code:
            try:
                if EnvelopeManager.Has_Envelope(project_code):
                    return EnvelopeManager.Get_Envelope(project_code)
                else:
                    project_code = EnvelopeManager.__get_project_parent_code(project_code)
            except XX_Project.DoesNotExist:
                project_code = None
        return None
    
    @staticmethod
    def Get_Total_Amount_for_Project(project_code, year=None, month=None):
        """
        Calculate total amount(total,from,to) for a project based on independent year and/or month filtering.
        
        Note: This function filters by:
        - transaction__transaction_date: 3-character month abbreviation (e.g., 'Jan', 'Feb', 'Mar')
        - transaction__fy: Last 2 digits of fiscal year (e.g., 25 for 2025, 24 for 2024)
        
        Usage Cases:
        1. Get all data without filter:
           Get_Total_Amount_for_Project('PRJ001')
           
        2. Get data for specific year only (using last 2 digits):
           Get_Total_Amount_for_Project('PRJ001', year=25)  # for 2025
           
        3. Get data for specific month only (across all years):
           Get_Total_Amount_for_Project('PRJ001', month=9)  # All September transactions
           
        4. Get data for specific year and month:
           Get_Total_Amount_for_Project('PRJ001', year=25, month=9)  # September 2025
           
        Note: Year and month parameters work independently - you can use either one or both.
        
        Args:
            project_code (str): Project code to filter by
            year (int, optional): Last 2 digits of fiscal year (e.g., 25 for 2025)
            month (int, optional): Month number (1-12, works independently of year)
            
        Returns:
            Decimal: Total amount calculated as (from_center * -1) + to_center
        """
        try:
            from django.db.models import Sum, F, Value, Q
            from django.db.models.functions import Coalesce
            import calendar
            
            # Start with base filter for project code
            transactions = xx_TransactionTransfer.objects.filter(project_code=project_code)
            
            # Apply date filtering based on provided parameters
            if year is not None:
                # Filter by fiscal year (last 2 digits)
                transactions = transactions.filter(transaction__fy=year)
                
            if month is not None:
                # Filter by specific month using 3-character abbreviation
                month_abbr = calendar.month_abbr[month]  # Convert month number to abbreviation
                transactions = transactions.filter(transaction__transaction_date=month_abbr)
            # If no year provided, get all data (no additional filter needed)
            
            # Calculate total amount: (from_center * -1) + to_center
            # Using Coalesce to handle null values, treating them as 0
            result = transactions.aggregate(
                total_from=Coalesce(Sum('from_center'), Value(0)),
                total_to=Coalesce(Sum('to_center'), Value(0))
            )
            
            # Calculate final total: subtract from_center and add to_center

            total_from = result['total_from'] * -1
            total_to =  result['total_to']
            total_amount = total_from + total_to
            
            return total_amount , total_from , total_to
            
        except Exception as e:
            print(f"Error calculating total amount for project {project_code}: {e}")
            return 0


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



