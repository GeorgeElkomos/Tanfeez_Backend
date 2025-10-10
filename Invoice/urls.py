from django.urls import path


from .views import (
     Invoice_extraction,
     Invoice_Crud,
)


urlpatterns = [
    # Account URLs
    path("Invoice_Crud/", Invoice_Crud.as_view(), name="invoice-crud"),
    path("Invoice_extraction/", Invoice_extraction.as_view(), name="invoice-extraction"),

]
