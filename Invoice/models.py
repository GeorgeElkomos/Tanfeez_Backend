from django.db import models
from user_management.models import xx_User
# Avoid importing xx_User at module import time to prevent circular imports

# Removed encrypted fields import - using standard Django fields now
import json


class xx_Invoice(models.Model):
    """Model to track invoices"""

    Invoice_ID = models.AutoField(primary_key=True)
    Invoice_Number = models.CharField(max_length=100, unique=True)
    Invoice_Data = models.JSONField()
    uploaded_by = models.ForeignKey(xx_User, on_delete=models.CASCADE)
    base64_file = models.TextField(default="")
    file_name= models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=50, default="Pending")  # e.g., Pending, Processed, Error
    class Meta:
        db_table = "XX_INVOICE_XX"

    def __str__(self):
        return f"Invoice {self.Invoice_ID}: {self.Invoice_Number} requested by {self.uploaded_by}"