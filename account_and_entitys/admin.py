from django.contrib import admin
from .models import XX_Account, XX_Entity, XX_PivotFund, XX_Project, XX_BalanceReport


@admin.register(XX_Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "parent", "alias_default")
    search_fields = ("account", "alias_default")
    list_filter = ("parent",)


@admin.register(XX_Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "parent", "alias_default")
    search_fields = ("project", "alias_default")
    list_filter = ("parent",)


@admin.register(XX_Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ("id", "entity", "parent", "alias_default")
    search_fields = ("entity", "alias_default")
    list_filter = ("parent",)


@admin.register(XX_PivotFund)
class PivotFundAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "entity",
        "account",
        "project",
        "year",
        "budget",
        "fund",
        "actual",
        "encumbrance",
    )
    list_filter = ("year",)
    search_fields = ("entity__entity", "account__account", "project__project")


@admin.register(XX_BalanceReport)
class BalanceReportAdmin(admin.ModelAdmin):
    """Admin interface for Balance Report model"""
    list_display = (
        "id",
        "control_budget_name",
        "ledger_name", 
        "as_of_period",
        "segment1",
        "segment2", 
        "segment3",
        "budget_ytd",
        "actual_ytd",
        "funds_available_asof",
        "created_at"
    )
    list_filter = (
        "control_budget_name",
        "ledger_name", 
        "as_of_period",
        "created_at"
    )
    search_fields = (
        "control_budget_name",
        "ledger_name",
        "segment1", 
        "segment2",
        "segment3"
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("control_budget_name", "ledger_name", "as_of_period")
        }),
        ("Segments", {
            "fields": ("segment1", "segment2", "segment3")
        }),
        ("Financial Data", {
            "fields": (
                "encumbrance_ytd", 
                "other_ytd", 
                "actual_ytd", 
                "funds_available_asof", 
                "budget_ytd"
            )
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        })
    )


# @admin.register(MainCurrency)
# class MainCurrencyAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'icon')
#     search_fields = ('name',)
#     list_filter = ('name',)

# @admin.register(MainRoutesName)
# class MainRoutesNameAdmin(admin.ModelAdmin):
#     list_display = ('id', 'english_name', 'arabic_name')
#     search_fields = ('english_name', 'arabic_name')
#     list_filter = ('english_name',)
