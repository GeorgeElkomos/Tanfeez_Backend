from django.urls import path
from .views import (
    AdjdTransactionTransferCreateView,
    AdjdTransactionTransferListView,
    AdjdTransactionTransferDetailView,
    AdjdTransactionTransferUpdateView,
    AdjdTransactionTransferDeleteView,
    AdjdtranscationtransferSubmit,
    Adjdtranscationtransfer_Reopen,
    AdjdTransactionTransferExcelUploadView,
)

urlpatterns = [
    # List and create endpoints
    path('', AdjdTransactionTransferListView.as_view(), name='adjd-transfer-list'),
    path('create/', AdjdTransactionTransferCreateView.as_view(), name='adjd-transfer-create'),
    
    # Detail, update, delete endpoints
    # path('<int:pk>/', AdjdTransactionTransferDetailView.as_view(), name='adjd-transfer-detail'),
    path('<int:pk>/update/', AdjdTransactionTransferUpdateView.as_view(), name='adjd-transfer-update'),
    path('<int:pk>/delete/', AdjdTransactionTransferDeleteView.as_view(), name='adjd-transfer-delete'),
    
    # Submit and reopen endpoints
    path('submit/', AdjdtranscationtransferSubmit.as_view(), name='adjd-transfer-submit'),
    path('reopen/', Adjdtranscationtransfer_Reopen.as_view(), name='adjd-transfer-reopen'),

    # Excel upload endpoint
    path('excel-upload/', AdjdTransactionTransferExcelUploadView.as_view(), name='adjd-transfer-excel-upload'),
]