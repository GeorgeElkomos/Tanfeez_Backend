from django.urls import path

from .views import (
     Invoice_extraction,
     Invoice_Crud,
     Invoice_submit
)


urlpatterns = [
    # Account URLs
    path("Invoice_Crud/", Invoice_Crud.as_view(), name="invoice-crud"),
    path("Invoice_extraction/", Invoice_extraction.as_view(), name="invoice-extraction"),
    path("Submit/", Invoice_submit.as_view(), name="invoice-extraction-detail"),

]
