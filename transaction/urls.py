from django.urls import path
from .views import (
    TransactionTransferCreateView,
    TransactionTransferListView,
    TransactionTransferDetailView,
    TransactionTransferUpdateView,
    TransactionTransferDeleteView,
    transcationtransferSubmit,
    transcationtransfer_Reopen,
    TransactionTransferExcelUploadView,
    BudgetQuestionAnswerView,
)

urlpatterns = [
    # List and create endpoints
    path("", TransactionTransferListView.as_view(), name="transfer-list"),
    path("create/", TransactionTransferCreateView.as_view(), name="transfer-create"),
    # Detail, update, delete endpoints
    # path('<int:pk>/', TransactionTransferDetailView.as_view(), name='transfer-detail'),
    path(
        "<int:pk>/update/",
        TransactionTransferUpdateView.as_view(),
        name="transfer-update",
    ),
    path(
        "<int:pk>/delete/",
        TransactionTransferDeleteView.as_view(),
        name="transfer-delete",
    ),
    # Submit and reopen endpoints
    path("submit/", transcationtransferSubmit.as_view(), name="transfer-submit"),
    path("reopen/", transcationtransfer_Reopen.as_view(), name="transfer-reopen"),
    # Excel upload endpoint
    path(
        "excel-upload/",
        TransactionTransferExcelUploadView.as_view(),
        name="transfer-excel-upload",
    ),
    # Budget Q&A endpoint
    path(
        "budget-qa/",
        BudgetQuestionAnswerView.as_view(),
        name="budget-question-answer",
    ),
]
