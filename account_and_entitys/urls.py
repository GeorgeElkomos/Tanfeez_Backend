from django.urls import path
from .views import (
    AccountListView, AccountCreateView, AccountDetailView, AccountUpdateView, AccountDeleteView,
    EntityListView, EntityCreateView, EntityDetailView, EntityUpdateView, EntityDeleteView,
    PivotFundListView, PivotFundCreateView, PivotFundDetailView, PivotFundUpdateView, PivotFundDeleteView,
    AdjdTransactionAuditListView, AdjdTransactionAuditCreateView, AdjdTransactionAuditDetailView, 
    AdjdTransactionAuditUpdateView, AdjdTransactionAuditDeleteView, ProjectCreateView, ProjectDeleteView, ProjectDetailView, ProjectListView, ProjectUpdateView, list_ACCOUNT_ENTITY_LIMIT,UpdateAccountEntityLimit,DeleteAccountEntityLimit,AccountEntityLimitAPI
   
)

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
    path("projects/create/", ProjectCreateView.as_view(), name="project-create"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path(
        "projects/<int:pk>/update/", ProjectUpdateView.as_view(), name="project-update"
    ),
    path(
        "projects/<int:pk>/delete/", ProjectDeleteView.as_view(), name="project-delete"
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
        AdjdTransactionAuditListView.as_view(),
        name="transaction-audit-list",
    ),
    path(
        "transaction-audits/create/",
        AdjdTransactionAuditCreateView.as_view(),
        name="transaction-audit-create",
    ),
    path(
        "transaction-audits/<int:pk>/",
        AdjdTransactionAuditDetailView.as_view(),
        name="transaction-audit-detail",
    ),
    path(
        "transaction-audits/<int:pk>/update/",
        AdjdTransactionAuditUpdateView.as_view(),
        name="transaction-audit-update",
    ),
    path(
        "transaction-audits/<int:pk>/delete/",
        AdjdTransactionAuditDeleteView.as_view(),
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
    # Main Currency URLs
]
