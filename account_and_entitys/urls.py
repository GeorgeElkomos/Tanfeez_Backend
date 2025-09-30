from django.urls import path
from .views import (
    AccountListView,
    AccountCreateView,
    AccountDetailView,
    AccountUpdateView,
    AccountDeleteView,
    EntityListView,
    EntityCreateView,
    EntityDetailView,
    EntityUpdateView,
    EntityDeleteView,
    PivotFundListView,
    PivotFundCreateView,
    PivotFundDetailView,
    PivotFundUpdateView,
    PivotFundDeleteView,
    ProjectEnvelopeListView,
    ProjectWiseDashboardView,
    TransactionAuditListView,
    TransactionAuditCreateView,
    TransactionAuditDetailView,
    TransactionAuditUpdateView,
    TransactionAuditDeleteView,
    ProjectCreateView,
    ProjectDeleteView,
    ProjectDetailView,
    ProjectListView,
    ProjectUpdateView,
    Upload_ProjectEnvelopeView,
    list_ACCOUNT_ENTITY_LIMIT,
    UpdateAccountEntityLimit,
    DeleteAccountEntityLimit,
    AccountEntityLimitAPI,
    RefreshBalanceReportView,
    BalanceReportListView,
    BalanceReportSegmentsView,
    BalanceReportFinancialDataView,
    Single_BalanceReportView,
    Upload_ProjectsView,
    Upload_AccountsView,
    Upload_EntitiesView,
    UploadAccountMappingView,
    UploadBudgetDataView,
    # UploadMappingExcelView,
    # AccountMappingListView,
    # EntityMappingListView,
    # AccountMappingDetailView,
    # EntityMappingDetailView
)
from .views import ActiveProjectsWithEnvelopeView

urlpatterns = [
    # Account URLs
    path("accounts/", AccountListView.as_view(), name="account-list"),
    path("accounts/create/", AccountCreateView.as_view(), name="account-create"),
    path("accounts/<int:pk>/", AccountDetailView.as_view(), name="account-detail"),
    path(
        "accounts/<int:pk>/update/", AccountUpdateView.as_view(), name="account-update"
    ),
    path(
        "accounts/<int:pk>/delete/", AccountDeleteView.as_view(), name="account-delete"
    ),
    # Project URLs
    path("projects/", ProjectListView.as_view(), name="project-list"),
    path(
        "projects/envelope/", ProjectEnvelopeListView.as_view(), name="project-envelope"
    ),
    path("projects/create/", ProjectCreateView.as_view(), name="project-create"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path(
        "projects/<int:pk>/update/", ProjectUpdateView.as_view(), name="project-update"
    ),
    path(
        "projects/<int:pk>/delete/", ProjectDeleteView.as_view(), name="project-delete"
    ),
    path(
        "projects/upload/",
        Upload_ProjectsView.as_view(),
        name="upload-projects",
    ),
    path(
        "accounts/upload/",
        Upload_AccountsView.as_view(),
        name="upload-accounts",
    ),
    path(
        "entities/upload/",
        Upload_EntitiesView.as_view(),
        name="upload-entities",
    ),
    path(
        "projects/envelope/upload/",
        Upload_ProjectEnvelopeView.as_view(),
        name="upload-project-envelope",
    ),
    path(
        "projects/active-with-envelope/",
        ActiveProjectsWithEnvelopeView.as_view(),
        name="active-projects-with-envelope",
    ),
    # Entity URLs
    path("entities/", EntityListView.as_view(), name="entity-list"),
    path("entities/create/", EntityCreateView.as_view(), name="entity-create"),
    path("entities/<int:pk>/", EntityDetailView.as_view(), name="entity-detail"),
    path("entities/<int:pk>/update/", EntityUpdateView.as_view(), name="entity-update"),
    path("entities/<int:pk>/delete/", EntityDeleteView.as_view(), name="entity-delete"),
    # PivotFund URLs
    path("pivot-funds/", PivotFundListView.as_view(), name="pivotfund-list"),
    path("pivot-funds/create/", PivotFundCreateView.as_view(), name="pivotfund-create"),
    path(
        "pivot-funds/getdetail/", PivotFundDetailView.as_view(), name="pivotfund-detail"
    ),
    path(
        "pivot-funds/<int:pk>/update/",
        PivotFundUpdateView.as_view(),
        name="pivotfund-update",
    ),
    path(
        "pivot-funds/<int:pk>/delete/",
        PivotFundDeleteView.as_view(),
        name="pivotfund-delete",
    ),
    # ADJD Transaction Audit URLs
    path(
        "transaction-audits/",
        TransactionAuditListView.as_view(),
        name="transaction-audit-list",
    ),
    path(
        "transaction-audits/create/",
        TransactionAuditCreateView.as_view(),
        name="transaction-audit-create",
    ),
    path(
        "transaction-audits/<int:pk>/",
        TransactionAuditDetailView.as_view(),
        name="transaction-audit-detail",
    ),
    path(
        "transaction-audits/<int:pk>/update/",
        TransactionAuditUpdateView.as_view(),
        name="transaction-audit-update",
    ),
    path(
        "transaction-audits/<int:pk>/delete/",
        TransactionAuditDeleteView.as_view(),
        name="transaction-audit-delete",
    ),
    # Fix the URL for list_ACCOUNT_ENTITY_LIMIT view
    path(
        "account-entity-limit/list/",
        list_ACCOUNT_ENTITY_LIMIT.as_view(),
        name="account-entity-limits",
    ),
    path(
        "account-entity-limit/upload/",
        AccountEntityLimitAPI.as_view(),
        name="account-entity-limits",
    ),
    # Update and Delete URLs for Account Entity Limit
    path(
        "account-entity-limit/update/",
        UpdateAccountEntityLimit.as_view(),
        name="update_limit",
    ),
    path(
        "account-entity-limit/delete/",
        DeleteAccountEntityLimit.as_view(),
        name="delete_limit",
    ),
    # Balance Report URLs
    path(
        "balance-report/refresh/",
        RefreshBalanceReportView.as_view(),
        name="refresh-balance-report",
    ),
    path(
        "balance-report/list/",
        BalanceReportListView.as_view(),
        name="list-balance-report",
    ),
    path(
        "balance-report/segments/",
        BalanceReportSegmentsView.as_view(),
        name="balance-report-segments",
    ),
    path(
        "balance-report/financial-data/",
        BalanceReportFinancialDataView.as_view(),
        name="balance-report-financial-data",
    ),
    path(
        "balance-report/single_balance/",
        Single_BalanceReportView.as_view(),
        name="balance-report",
    ),
    path(
        "budget-data/upload/",
        UploadBudgetDataView.as_view(),
        name="upload-budget-data",
    ),
    # Mapping URLs
    path(
        "account-mapping/upload/",
        UploadAccountMappingView.as_view(),
        name="upload-account-mapping",
    ),
    # Mapping URLs
    path(
        "project-wise-dashboard/",
        ProjectWiseDashboardView.as_view(),
        name="project-wise-dashboard",
    ),
    # path(
    #     "mappings/upload-excel/",
    #     UploadMappingExcelView.as_view(),
    #     name="upload-mapping-excel",
    # ),
    # path(
    #     "mappings/accounts/",
    #     AccountMappingListView.as_view(),
    #     name="account-mapping-list",
    # ),
    # path(
    #     "mappings/accounts/<int:pk>/",
    #     AccountMappingDetailView.as_view(),
    #     name="account-mapping-detail",
    # ),
    # path(
    #     "mappings/entities/",
    #     EntityMappingListView.as_view(),
    #     name="entity-mapping-list",
    # ),
    # path(
    #     "mappings/entities/<int:pk>/",
    #     EntityMappingDetailView.as_view(),
    #     name="entity-mapping-detail",
    # ),
    # Main Currency URLs
]
