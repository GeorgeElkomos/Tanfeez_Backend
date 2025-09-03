from pyexpat import model
from django.db import models
from account_and_entitys.models import XX_Account, XX_Entity
from user_management.models import xx_User
# Removed encrypted fields import - using standard Django fields now
import json


class xx_BudgetTransfer(models.Model):
    """Model to track budget transfers between users"""
    transaction_id = models.AutoField(primary_key=True)
    transaction_date = models.CharField(max_length=10)  # Changed from EncryptedCharField to DateField
    amount = models.DecimalField(max_digits=15, decimal_places=2)  # Changed from EncryptedCharField to DecimalField
    status = models.CharField(max_length=10)
    requested_by = models.CharField(max_length=100, null=True, blank=True)  # Changed from EncryptedCharField
    user_id = models.IntegerField(null=True, blank=True)
    request_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)  # Keep as TextField but avoid in complex queries
    code = models.CharField(max_length=10, null=True, blank=True)
    gl_posting_status = models.CharField(max_length=50, null=True, blank=True)  # Changed from EncryptedCharField
    approvel_1 = models.CharField(max_length=100, null=True, blank=True)  # Changed from EncryptedCharField
    approvel_2 = models.CharField(max_length=100, null=True, blank=True)  # Changed from EncryptedCharField
    approvel_3 = models.CharField(max_length=100, null=True, blank=True)  # Changed from EncryptedCharField
    approvel_4 = models.CharField(max_length=100, null=True, blank=True)  # Changed from EncryptedCharField
    approvel_1_date = models.DateTimeField(null=True, blank=True)  # Changed from EncryptedDateTimeField
    approvel_2_date = models.DateTimeField(null=True, blank=True)  # Changed from EncryptedDateTimeField
    approvel_3_date = models.DateTimeField(null=True, blank=True)  # Changed from EncryptedDateTimeField
    approvel_4_date = models.DateTimeField(null=True, blank=True)  # Changed from EncryptedDateTimeField
    status_level = models.IntegerField(default=1)
    attachment = models.CharField(max_length=10, null=True, blank=True, default="No")  # Changed from EncryptedCharField
    fy = models.IntegerField(null=True, blank=True)  # Changed from EncryptedIntegerField
    group_id = models.IntegerField(null=True, blank=True)
    interface_id = models.IntegerField(null=True, blank=True)
    reject_group_id = models.IntegerField(null=True, blank=True)
    reject_interface_id = models.IntegerField(null=True, blank=True)
    approve_group_id = models.IntegerField(null=True, blank=True)
    approve_interface_id = models.IntegerField(null=True, blank=True)
    report = models.CharField(max_length=10, null=True, blank=True)  # Changed from EncryptedCharField
    type = models.CharField(max_length=10, null=True, blank=True)  # Changed from EncryptedCharField
    
    class Meta:
        db_table = 'XX_BUDGET_TRANSFER_XX'
    
    def __str__(self):
        return f"Transfer {self.transaction_id}: {self.amount} requested by {self.requested_by}"

# SELECT * FROM XX_BUDGET_TRANSFER_XX
# JOIN XX_Transaction_Transfer_XX ON XX_BUDGET_TRANSFER_XX.transaction_id = XX_Transaction_Transfer_XX.transaction_id 
# JOIN XX_Entity_XX ON XX_Transaction_Transfer_XX.cost_center_code = XX_Entity_XX.entity 
# WHERE XX_Entity_XX.id IN (value1, value2, ...);

from django.db.models import Q, Count, F
from django.db.models import Value
from django.db.models.functions import Cast
from django.db.models import CharField

def get_entities_with_children(entity_ids):
    """
    Given a list of entity IDs, return all XX_Entity objects including their children (recursively).
    """
    # Start with the initial set
    entities = list(XX_Entity.objects.filter(id__in=entity_ids))
    collected_ids = set(e.id for e in entities)

    queue = list(entities)  # start with base entities
    while queue:
        parent_entity = queue.pop(0)

        # Find children where parent matches the string version of this entity number
        children = XX_Entity.objects.filter(parent=str(parent_entity.entity))

        for child in children:
            if child.id not in collected_ids:
                collected_ids.add(child.id)
                entities.append(child)
                queue.append(child)

    return entities

def get_zero_level_accounts(accounts_queryset):
    """
    Given a queryset of XX_Account objects, return only Zero Level accounts
    (accounts that are not parents to any other account).
    """
    # Convert queryset to list if it's not already
    accounts = list(accounts_queryset)
    
    # Get all account numbers that are used as parents
    parent_accounts = XX_Account.objects.exclude(parent__isnull=True).exclude(parent='')
    parent_account_numbers = set(parent.parent for parent in parent_accounts)
    
    # Filter for accounts that are not parents
    zero_level_accounts = [
        account for account in accounts 
        if account.account not in parent_account_numbers
    ]
    
    return zero_level_accounts

def filter_budget_transfers_all_in_entities(budget_transfers, user, Type = 'edit',dashboard_filler_per_project=None):
    """
    From a given queryset of BudgetTransfer objects,
    return only those where *all* related transactions
    belong to the given entity_ids.
    
    Modified to avoid Oracle NCLOB issues with complex annotations.
    """
    entity_ids = [ability.Entity.id for ability in user.abilities.all() if ability.Entity and ability.Type == Type]
    if dashboard_filler_per_project is not None:
        if int(dashboard_filler_per_project) in entity_ids:
            entity_ids = [int(dashboard_filler_per_project)]
    entities = get_entities_with_children(entity_ids)

    # Collect allowed entity codes and convert to integers when possible to match numeric cost_center_code
    raw_entity_codes = [e.entity for e in entities]
    numeric_entity_codes = []
    for code in raw_entity_codes:
        try:
            # Many entities are stored as strings but represent integers; convert safely
            numeric_entity_codes.append(int(str(code).strip()))
        except Exception:
            # Skip non-numeric codes to avoid Oracle ORA-01722 when comparing to NUMBER columns
            continue

    # Simplified approach to avoid NCLOB issues
    # Get transfer IDs that have all their transactions in allowed entities
    from django.db import connection
    
    try:
        # Use raw SQL to avoid NCLOB issues with complex annotations
        with connection.cursor() as cursor:
            if numeric_entity_codes:
                # Build dynamic placeholders for IN clause
                placeholders = ','.join(['%s'] * len(numeric_entity_codes))
                sql = f"""
                    SELECT bt.transaction_id
                    FROM XX_BUDGET_TRANSFER_XX bt
                    WHERE NOT EXISTS (
                        SELECT 1 
                        FROM XX_Transaction_Transfer_XX tt 
                        WHERE tt.transaction_id = bt.transaction_id 
                        AND tt.cost_center_code NOT IN ({placeholders})
                    )
                    AND EXISTS (
                        SELECT 1 
                        FROM XX_Transaction_Transfer_XX tt2 
                        WHERE tt2.transaction_id = bt.transaction_id
                    )

                    UNION

                    SELECT bt.transaction_id
                    FROM XX_BUDGET_TRANSFER_XX bt
                    WHERE NOT EXISTS (
                        SELECT 1 
                        FROM XX_Transaction_Transfer_XX tt 
                        WHERE tt.transaction_id = bt.transaction_id
                    )
                """
                cursor.execute(sql, numeric_entity_codes)
            else:
                # No numeric entity codes; skip NOT IN check and just select those with no transactions
                cursor.execute(
                    """
                    SELECT bt.transaction_id
                    FROM XX_BUDGET_TRANSFER_XX bt
                    WHERE NOT EXISTS (
                        SELECT 1 
                        FROM XX_Transaction_Transfer_XX tt 
                        WHERE tt.transaction_id = bt.transaction_id
                    )
                    """
                )

            allowed_ids = [row[0] for row in cursor.fetchall()]
        
        combined = budget_transfers.filter(
            Q(transaction_id__in=allowed_ids) | Q(user_id=user.id)
        ).distinct()
        return combined

    except Exception as e:
        # Fallback to simple filtering if raw SQL fails
        print(f"Error occurred: {e}")
        if numeric_entity_codes:
            return budget_transfers.filter(
                Q(adjd_transfers__cost_center_code__in=numeric_entity_codes) | Q(user_id=user.id)
            ).distinct()
        # If nothing numeric to filter on, just fall back to user-owned transfers
        return budget_transfers.filter(Q(user_id=user.id)).distinct()

def get_level_zero_children(entity_ids):
    """
    Given a list of entity IDs, return only the Level 0 children 
    (children that are not parents to any other entity).
    """
    # First get all entities including their children recursively
    all_entities = get_entities_with_children(entity_ids)
    
    # Create a set of all entity numbers that are parents
    parent_numbers = set()
    for entity in all_entities:
        if entity.parent:  # If this entity has a parent
            parent_numbers.add(entity.parent)
    
    # Filter for entities that are not parents (level 0 children)
    level_zero_children = []
    for entity in all_entities:
        # Check if this entity's number is NOT in parent_numbers
        # and also make sure it's not one of the original entities (if needed)
        if str(entity.entity) not in parent_numbers:
            level_zero_children.append(entity)
    
    return level_zero_children





def get_costcenter_code(user, Type = 'edit',dashboard_filler_per_project=None):
    """
    From a given queryset of BudgetTransfer objects,
    return only those where *all* related transactions
    belong to the given entity_ids.
    
    Modified to avoid Oracle NCLOB issues with complex annotations.
    """
    entity_ids = [ability.Entity.id for ability in user.abilities.all() if ability.Entity and ability.Type == Type]
    if len(dashboard_filler_per_project) > 0:
            if all(entity_id in entity_ids for entity_id in dashboard_filler_per_project):
               entity_ids = dashboard_filler_per_project
    entities = get_entities_with_children(entity_ids)
    entity_codes = [e.entity for e in entities]
    return entity_codes

    

class xx_BudgetTransferAttachment(models.Model):
    """Model to store file attachments as BLOBs for budget transfers"""
    attachment_id = models.AutoField(primary_key=True)
    budget_transfer = models.ForeignKey(
        xx_BudgetTransfer, 
        on_delete=models.CASCADE,
        related_name='attachments',
        db_column='transaction_id'
    )
    file_name = models.CharField(max_length=255)  # Changed from EncryptedCharField
    file_type = models.CharField(max_length=100)  # Changed from EncryptedCharField
    file_size = models.IntegerField()
    file_data = models.BinaryField()  # This will store the BLOB data
    upload_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'XX_BUDGET_TRANSFER_ATTACHMENT_XX'
        
    def __str__(self):
        return f"Attachment {self.attachment_id}: {self.file_name} for Transfer {self.budget_transfer_id}"


class xx_BudgetTransferRejectReason(models.Model):
    """Model to store reject reasons for budget transfers"""
    Transcation_id = models.ForeignKey(
        xx_BudgetTransfer,
        on_delete=models.CASCADE,
        related_name='reject_reasons'
    )
    reason_text = models.TextField(null=True, blank=True)  # Keep as TextField but avoid in complex queries

    reject_date = models.DateTimeField(auto_now_add=True)  # Changed from EncryptedDateTimeField

    reject_by = models.CharField(max_length=100, null=False, blank=True)  # Changed from EncryptedCharField


    class Meta:
        db_table = 'XX_BUDGET_TRANSFER_REJECT_REASON_XX'
        
    def __str__(self):
        return f"Reject Reason for Transfer {self.budget_transfer_id}: {self.reason_text}"




class xx_DashboardBudgetTransfer(models.Model):
    """Model to store dashboard data for budget transfers"""
    Dashboard_id = models.AutoField(primary_key=True)
    data = models.TextField(null=True, blank=True)  # Keep as TextField but avoid in complex queries
    date = models.DateTimeField(auto_now_add=True)  # Changed from EncryptedDateTimeField
    
    def set_data(self, data_dict):
        """Helper method to store dictionary as JSON string"""
        self.data = json.dumps(data_dict)
    
    def get_data(self):
        """Helper method to retrieve JSON data as dictionary"""
        if self.data:
            return json.loads(self.data)
        return None
    
    class Meta:
        db_table = 'XX_DASHBOARD_BUDGET_TRANSFER_XX'
    
    def __str__(self):
        return f"Dashboard Data {self.Dashboard_id} from {self.date}"