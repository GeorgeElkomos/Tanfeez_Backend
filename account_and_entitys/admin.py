from django.contrib import admin
from .models import XX_Account, XX_Entity, XX_PivotFund, XX_Project


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
