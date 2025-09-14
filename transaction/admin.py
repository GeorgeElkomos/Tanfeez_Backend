from django.contrib import admin
from .models import xx_TransactionTransfer


@admin.register(xx_TransactionTransfer)
class TransactionTransferAdmin(admin.ModelAdmin):
    list_display = (
        "transfer_id",
        "cost_center_code",
        "account_name",
        "project_name",
        "transaction",
        "done",
    )
    list_filter = ("done",)
    search_fields = (
        "cost_center_code",
        "cost_center_name",
        "account_name",
        "account_code",
        "project_code",
        "project_name",
    )
    raw_id_fields = ("transaction",)
