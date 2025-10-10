from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import xx_Invoice as Invoice
from .serializers import InvoiceSerializer
from .AI.Gemini_model import  extract_invoice_with_gemini
from .AI.Own_model import extract_invoice_with_deepseek 


class InvoicePagination(PageNumberPagination):
    """Pagination class for invoices"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100



class Invoice_extraction(APIView):
    """Extract invoices"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Placeholder for extraction logic

        file = request.FILES.get("file")
        model_choice = request.data.get("model", "own")  # Default to own model if not provided
        
        if not file:
            return Response(
                {"message": "No file uploaded."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if model_choice == "gemini":
            extracted_data = extract_invoice_with_gemini(file)
        elif model_choice == "own":
            extracted_data = extract_invoice_with_deepseek(file)

        if not extracted_data:
            return Response(
                {"message": "Invoice extraction failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        

        return Response(
            {"message": "Invoice extraction logic not implemented."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )





class Invoice_Crud(APIView):
    """Create invoices"""

    permission_classes = [IsAuthenticated]

    def post(self, request):

        if not request.data.get("Invoice_Data") and request.data.get("Invoice_Number") != []:
            return Response(
                {
                    "message": "Invoice date is a required field.",
                    "errors": {
                        "Invoice_Data": (
                            "This field is required."
                            if not request.data.get("Invoice_Data")
                            else None
                        )
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        Invoice_details=request.data.get("Invoice_Data")
        serializer = InvoiceSerializer(data={
            "Invoice_Data": Invoice_details,
            "Invoice_Number": request.data.get("Invoice_Number"),
            "uploaded_by": request.user.id
        })

        if serializer.is_valid():
            invoice = serializer.save()
            return Response(
                {
                    "message": "Invoice created successfully.",
                    "data": InvoiceSerializer(invoice).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """List all invoices with pagination"""
        Invoice_Number = request.query_params.get("Invoice_Number", None)

        if Invoice_Number:
            invoices = Invoice.objects.filter(Invoice_Number=Invoice_Number)
        else:
            invoices = Invoice.objects.all()
            
        paginator = InvoicePagination()
        paginated_invoices = paginator.paginate_queryset(invoices, request)
        serializer = InvoiceSerializer(paginated_invoices, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def delete(self, request):
        """Delete an invoice by ID"""
        try:
            Invoice_Number = request.query_params.get("Invoice_Number", None)

            invoice = Invoice.objects.get(Invoice_Number=Invoice_Number)
        except Invoice.DoesNotExist:
            return Response(
                {"message": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        invoice.delete()
        return Response(
            {"message": "Invoice deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )
    
    def put(self, request):
        """Update an invoice - Delete old data and replace with new JSON"""
        try:
            Invoice_Number = request.data.get("Invoice_Number")
            
            if not Invoice_Number:
                return Response(
                    {"message": "Invoice_Number is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Find the existing invoice
            invoice = Invoice.objects.get(Invoice_Number=Invoice_Number)
            
            # Delete the old invoice
            invoice.delete()
            
            # Create new invoice with the provided data
            new_data = {
                "Invoice_Number": Invoice_Number,
                "Invoice_Data": request.data.get("Invoice_Data"),
                "uploaded_by": request.user.id
            }
            
            serializer = InvoiceSerializer(data=new_data)
            if serializer.is_valid():
                new_invoice = serializer.save()
                return Response(
                    {
                        "message": "Invoice replaced successfully.",
                        "data": InvoiceSerializer(new_invoice).data,
                    },
                    status=status.HTTP_200_OK,
                )
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Invoice.DoesNotExist:
            return Response(
                {"message": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"message": f"Error updating invoice: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

