from django.urls import path
from .views import (
    CreateBudgetTransferView, 
    ListBudgetTransferView, 
    ApproveBudgetTransferView, 
    GetBudgetTransferView,
    UpdateBudgetTransferView,
    DeleteBudgetTransferView,
    Adjdtranscationtransferapprovel_reject,
    ListBudgetTransfer_approvels_View,
    BudgetTransferFileUploadView,
    DeleteBudgetTransferAttachmentView,
    ListBudgetTransferAttachmentsView,
    list_budget_transfer_reject_reason,
    DashboardBudgetTransferView,
    ListBudgetTransfer_approvels_MobileView
)

app_name = 'budget_management'

urlpatterns = [
    # Budget transfer endpoints
    path('transfers/create/', CreateBudgetTransferView.as_view(), name='create-budget-transfer'),
    path('transfers/list/', ListBudgetTransferView.as_view(), name='list-budget-transfers'),
    path('transfers/list_underapprovel/', ListBudgetTransfer_approvels_View.as_view(), name='list-budget-transfersus_underapprovel'),
    path('transfers/list_Mobile_underapprovel/', ListBudgetTransfer_approvels_MobileView.as_view(), name='list-budget-transfersus_underapprovel'),


    path('transfers/<int:transfer_id>/', GetBudgetTransferView.as_view(), name='get-budget-transfer'),
    path('transfers/<int:transfer_id>/update/', UpdateBudgetTransferView.as_view(), name='update-budget-transfer'),
    path('transfers/<int:transfer_id>/approve/', ApproveBudgetTransferView.as_view(), name='approve-budget-transfer'),
    path('transfers/<str:transfer_id>/delete/', DeleteBudgetTransferView.as_view(), name='delete-budget-transfer'),
    
    # URL for approve/reject ADJD transaction transfers
    path('transfers/adjd-approve-reject/', Adjdtranscationtransferapprovel_reject.as_view(), name='adjd-transaction-approve-reject'),

    # File upload and delete endpoints
    path('transfers/upload-files/', BudgetTransferFileUploadView.as_view(), name='budget-transfer-upload-files'),
    path('transfers/list-files/', ListBudgetTransferAttachmentsView.as_view(), name='budget-transfer-list-files'),

    path('transfers/<int:transfer_id>/attachments/<int:attachment_id>/', DeleteBudgetTransferAttachmentView.as_view(), name='budget-transfer-delete-attachment'),
    path('transfers/list_reject/', list_budget_transfer_reject_reason.as_view(), name='budget-transfer-delete-attachment'),


    path('dashboard/', DashboardBudgetTransferView.as_view(), name='dashboard-budget-transfer'),

]
