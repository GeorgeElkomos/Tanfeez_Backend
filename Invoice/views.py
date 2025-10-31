from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
import json
import re
import base64

from .models import xx_Invoice as Invoice
from .serializers import InvoiceSerializer
from .AI.Gemini_model import extract_invoice_with_gemini
from .AI.Own_model import extract_invoice_with_deepseek
from .utility import send_request

def clean_and_parse_json_response(response_text):
    """
    Clean and parse JSON response that may contain markdown code blocks.
    Preserves decimal precision (e.g., 300.20 stays as "300.20" string).
    
    Args:
        response_text (str): Raw response text that may contain ```json...``` blocks
        
    Returns:
        dict: Parsed JSON as dictionary with Decimal strings preserved, or None if parsing fails
        
    Example:
        Input: "```json\\n{\"amount\": 300.20}\\n```"
        Output: {"amount": "300.20"}  # Preserved as string to keep trailing zeros
    """
    if not response_text:
        return None
    
    try:
        from decimal import Decimal
        
        # Remove markdown code blocks (```json and ```)
        cleaned_text = response_text.strip()
        
        # Pattern to match ```json...``` or ```...```
        json_pattern = r'```(?:json)?\s*\n(.*?)\n```'
        match = re.search(json_pattern, cleaned_text, re.DOTALL)
        
        if match:
            # Extract JSON from code block
            json_str = match.group(1).strip()
        else:
            # No code block, use the whole text
            json_str = cleaned_text
        
        # Remove any leading/trailing whitespace
        json_str = json_str.strip()
        
        # Parse JSON with parse_float to preserve decimal precision
        parsed_json = json.loads(json_str, parse_float=Decimal)
        
        # Convert Decimals to strings to preserve trailing zeros
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {key: convert_decimals(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                # Convert Decimal to string, preserving format
                return str(obj)
            else:
                return obj
        
        result = convert_decimals(parsed_json)
        return result
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Attempted to parse: {json_str[:200]}...")
        return None
    except Exception as e:
        print(f"❌ Unexpected error cleaning JSON: {e}")
        return None


class InvoicePagination(PageNumberPagination):
    """Pagination class for invoices"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class Invoice_extraction(APIView):
    """Extract invoices"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Extract invoice data from PDF using AI models"""

        file = request.FILES.get("file")
        model_choice = request.data.get("model", "deepseek")  # Default to deepseek model if not provided
        
        if not file:
            return Response(
                {"message": "No file uploaded."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Extract data using selected model
        if model_choice != "own":
            raw_response = extract_invoice_with_gemini(file, model_name=model_choice)
        elif model_choice == "own":
            raw_response = extract_invoice_with_deepseek(file)
        else:
            return Response(
                {"message": f"Invalid model choice: {model_choice}. Use 'gemini' or 'own'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not raw_response:
            return Response(
                {"message": "Invoice extraction failed. No response from AI model."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        # Clean and parse the JSON response
        parsed_data = clean_and_parse_json_response(raw_response)# Get invoice number from parsed data
 
        
        if not parsed_data:
            return Response(
                {
                    "message": "Failed to parse AI response as JSON.",
                    "raw_response": raw_response[:500]  # Return first 500 chars for debugging
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        # Convert PDF to base64
        try:
            #read file name
            file_name = file.name
            # Reset file pointer to beginning
            file.seek(0)
            # Read file content
            pdf_content = file.read()

            # Encode to base64
            base64_encoded = base64.b64encode(pdf_content).decode('utf-8')
            
            # Get invoice number from parsed data
            Invoice_Number = parsed_data.get("InvoiceNumber", "UNKNOWN")
            
        except Exception as e:
            return Response(
                {
                    "message": f"Failed to encode PDF to base64: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": "Invoice extracted successfully.",
                "model_used": model_choice,
                "invoice_number": Invoice_Number,
                "pdf_base64": base64_encoded,
                "file_name": file_name,
                "data": parsed_data,  # Now returns clean parsed JSON
            },
            status=status.HTTP_200_OK
        )

class Invoice_submit(APIView):
     permission_classes = [IsAuthenticated]

     def post(self, request): 
            """Submit extracted invoice data to create an invoice record"""
            
            Invoice_Number = request.data.get("InvoiceNumber")

            if not Invoice_Number:
                return Response(
                    {
                        "message": " 'InvoiceNumber' are required fields.",
                        "errors": {
                            "InvoiceNumber": "This field is required." if not Invoice_Number else None,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            Invoice_Object = Invoice.objects.filter(Invoice_Number=Invoice_Number).first()
            
            
            if Invoice_Object:

                Invoice_data=Invoice_Object.Invoice_Data
                Invoice_data.pop("AccountCode", None)  # Remove existing AccountCode if any
                Invoice_data.pop("Account Description", None) # Remove existing Account Description if any
                  # Remove existing Account Description if any

                

                oracle_response = send_request(base64_content=Invoice_Object.base64_file, filename=Invoice_Object.file_name, json_data=Invoice_data, category="From Supplier")
                
                # Check if oracle_response indicates an error
                if oracle_response and isinstance(oracle_response, dict):
                    # Check for error indicators in the response
                    if oracle_response.get('status') == 'error':
                        Invoice_Object.status = "Error"
                        Invoice_Object.save()
                        return Response(
                            {
                                "message": "Invoice submission failed.",
                                "status_code": oracle_response.get('status_code'),
                                "error": oracle_response.get('error') or oracle_response.get('response_body'),
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    elif oracle_response.get('status') == 'success':
                        Invoice_Object.status = "Submitted"
                        Invoice_Object.save()
                        return Response(
                            {
                                "message": "Invoice submitted successfully.",
                                "status_code": oracle_response.get('status_code'),
                                "response_body": oracle_response.get('response_body'),
                            },
                            status=status.HTTP_200_OK,
                        )
                    else:
                        # Unknown status
                        Invoice_Object.status = "Error"
                        Invoice_Object.save()
                        return Response(
                            {
                                "message": "Invoice submission returned unknown status.",
                                "oracle_response": oracle_response
                            },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )
                else:
                    # If oracle_response is None or unexpected format
                    Invoice_Object.status = "Error"
                    Invoice_Object.save()
                    return Response(
                        {
                            "message": "Invoice submission failed - No response from Oracle.",
                            "oracle_response": oracle_response
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            else:
                return Response(
                    {
                        "message": "Invoice not found.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
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
                            if not request.data.get("Invoice_Object")
                            else None
                        )
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        Invoice_details=request.data.get("Invoice_Data")
        Invoice_file_name = request.data.get("file_name")
        Invoice_base64_file = request.data.get("base64_file")

        serializer = InvoiceSerializer(
        data={

            "Invoice_Data": Invoice_details,
            "Invoice_Number": request.data.get("Invoice_Number"),
            "uploaded_by": request.user.id,
            "file_name": Invoice_file_name,
            "base64_file": Invoice_base64_file,
        }
        )

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

        if not Invoice_Number:
            data = []
            for invoice in paginated_invoices:
                # Handle both string and dict types for Invoice_Object
                Invoice_Object = invoice.Invoice_Data if invoice.Invoice_Data else {}
                
                # If it's a string, parse it as JSON
                if isinstance(Invoice_Object, str):
                    try:
                        Invoice_Object = json.loads(Invoice_Object)
                    except json.JSONDecodeError:
                        Invoice_Object = {}
                
                # Extract only the required fields
                extracted_data = {
                    'status': invoice.status,
                    # 'file_name': invoice.file_name,
                    'InvoiceNumber': Invoice_Object.get('InvoiceNumber'),
                    'InvoiceCurrency': Invoice_Object.get('InvoiceCurrency'),
                    'InvoiceAmount': Invoice_Object.get('InvoiceAmount'),
                    'InvoiceDate': Invoice_Object.get('Invoice_Data'),
                    'BusinessUnit': Invoice_Object.get('BusinessUnit'),
                    'Supplier': Invoice_Object.get('Supplier'),
                    'SupplierSite': Invoice_Object.get('SupplierSite'),
                }
                data.append(extracted_data)
            return paginator.get_paginated_response(data)
        else:
            # When Invoice_Number is provided, parse the Invoice_Object
            data = []
            for invoice in paginated_invoices:
                # Handle both string and dict types for Invoice_Object
                Invoice_Object = invoice.Invoice_Data if invoice.Invoice_Data else {}
                
                # If it's a string, parse it as JSON
                if isinstance(Invoice_Object, str):
                    try:
                        Invoice_Object = json.loads(Invoice_Object)
                    except json.JSONDecodeError:
                        Invoice_Object = {}
                
                # Return all fields with parsed Invoice_Object
                extracted_data = {
                    'Invoice_ID': invoice.Invoice_ID,
                    'Invoice_Number': invoice.Invoice_Number,
                    'InvoiceDate': Invoice_Object.get('Invoice_Data'),
                    'uploaded_by': invoice.uploaded_by.id if invoice.uploaded_by else None,
                    'base64_file': invoice.base64_file,
                    'file_name': invoice.file_name,
                    'status': invoice.status
                }
                data.append(extracted_data)
            
            return paginator.get_paginated_response(data)


    
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
                "Invoice_Object": request.data.get("Invoice_Object"),
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

