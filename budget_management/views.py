from datetime import time
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q, Sum
from django.db.models.functions import Cast
from django.db.models import CharField
from user_management.models import xx_notification
from .models import (
    filter_budget_transfers_all_in_entities,
    xx_BudgetTransfer,
    xx_BudgetTransferAttachment,
    xx_BudgetTransferRejectReason,
    xx_DashboardBudgetTransfer,
)
from account_and_entitys.models import XX_PivotFund, XX_Entity, XX_Account
from adjd_transaction.models import xx_TransactionTransfer
from .serializers import BudgetTransferSerializer
from user_management.permissions import IsAdmin, CanTransferBudget
from budget_transfer.global_function.dashbaord import (
    get_all_dashboard_data, 
    get_saved_dashboard_data, 
    refresh_dashboard_data
)
from public_funtion.update_pivot_fund import update_pivot_fund
import base64
from django.db.models.functions import Cast
from django.db.models import CharField
from collections import defaultdict
from django.db.models import Prefetch
from collections import defaultdict
from decimal import Decimal
import time
import multiprocessing
from itertools import islice
from decimal import Decimal
import multiprocessing
from collections import defaultdict
from decimal import Decimal
import time
from itertools import islice
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, Count, Case, When, Value, F


class TransferPagination(PageNumberPagination):
    """Pagination class for budget transfers"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
class CreateBudgetTransferView(APIView):
    """Create budget transfers"""

    permission_classes = [IsAuthenticated]

    def post(self, request):

        if not request.data.get("transaction_date") or not request.data.get("notes"):
            return Response(
                {
                    "message": "Transaction date and notes are required fields.",
                    "errors": {
                        "transaction_date": (
                            "This field is required."
                            if not request.data.get("transaction_date")
                            else None
                        ),
                        "notes": (
                            "This field is required."
                            if not request.data.get("notes")
                            else None
                        ),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        transfer_type = request.data.get("type").upper()

        if transfer_type in ["FAR", "AFR", "FAD"]:
            prefix = f"{transfer_type}-"
        else:

            prefix = "FAR-"
            

        last_transfer = (
                xx_BudgetTransfer.objects
                .filter(code__startswith=prefix)
                .order_by("-code")
                .first()
            )

        if last_transfer and last_transfer.code:
            try:
                last_num = int(last_transfer.code.replace(prefix, ""))
                new_num = last_num + 1
            except (ValueError, AttributeError):

                new_num = 1
        else:

            new_num = 1

        new_code = f"{prefix}{new_num:04d}"

        serializer = BudgetTransferSerializer(data=request.data)

        if serializer.is_valid():

            transfer = serializer.save(
                requested_by=request.user.username,
                user_id=request.user.id,
                status="pending",
                request_date=timezone.now(),
                code=new_code,
            )
            Notification_object = xx_notification.objects.create(
                user_id=request.user.id,
                message=f"New budget transfer request created with code {new_code}",
            )
            Notification_object.save()
            return Response(
                {
                    "message": "Budget transfer request created successfully.",
                    "data": BudgetTransferSerializer(transfer).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class ListBudgetTransferView(APIView):
    """List budget transfers with pagination"""

    permission_classes = [IsAuthenticated]
    pagination_class = TransferPagination

    def get(self, request):
        status_type = request.query_params.get("status_type", None)
        search = request.query_params.get("search")
        day = request.query_params.get("day")
        month = request.query_params.get("month")
        year = request.query_params.get("year")
        sdate = request.query_params.get("start_date")
        edate = request.query_params.get("end_date")
        code = request.query_params.get("code", None)


        if request.user.role == "admin":
            if status_type:
                transfers = xx_BudgetTransfer.objects.filter(status=status_type)
            else:
                transfers = xx_BudgetTransfer.objects.all()
        else:
            if status_type:
                transfers = xx_BudgetTransfer.objects.filter(status=status_type,user_id=request.user.id)
            else:
                transfers = xx_BudgetTransfer.objects.filter(user_id=request.user.id)

        # print(type(code))


        if code:
            # Coerce to string first and use upper() to avoid errors if a non-string is provided
            print(code)
            code_upper = code.upper()
            transfers = transfers.filter(type=code_upper)


        if request.user.abilities.count() > 0:
            transfers = filter_budget_transfers_all_in_entities(budget_transfers=transfers, user=request.user, Type='edit')

        # Free-text search across common fields (icontains)
        if search:
            s = str(search).strip()
            query = (
                Q(code__icontains=s)
                | Q(requested_by__icontains=s)
                | Q(status__icontains=s)
                | Q(transaction_date__icontains=s)
                | Q(type__icontains=s)
            )
            if s.isdigit():
                # Support numeric search on transaction_id
                try:
                    query |= Q(transaction_id=int(s))
                except Exception:
                    pass
            transfers = transfers.filter(query)
        
        try:
            from datetime import datetime as _dt

            def _validate(fmt, value):
                try:
                    _dt.strptime(value, fmt)
                    return True
                except Exception:
                    return False
                
            if day:
                if not _validate("%Y-%m-%d", day):
                    return Response({"error": "Invalid day format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)
                transfers = transfers.filter(request_date__startswith=day)
            elif month:
                mval = str(month)
                prefix = None
                if _validate("%Y-%m", mval):
                    prefix = mval
                else:
                    if year:
                        try:
                            yi = int(year)
                            mi = int(mval)
                            if 1 <= mi <= 12 and 1900 <= yi <= 2100:
                                prefix = f"{yi}-{mi:02d}"
                        except Exception:
                            pass
                if not prefix:
                    return Response({"error": "Invalid month. Provide YYYY-MM or month with 'year'"}, status=status.HTTP_400_BAD_REQUEST)
                transfers = transfers.filter(request_date__startswith=prefix)
            elif year:
                try:
                    yi = int(year)
                    if yi < 1900 or yi > 2100:
                        raise ValueError()
                except Exception:
                    return Response({"error": "Invalid year. Use YYYY in range 1900-2100"}, status=status.HTTP_400_BAD_REQUEST)
                transfers = transfers.filter(request_date__startswith=f"{int(year)}-")
            elif sdate and edate:
                sd = str(sdate)
                ed = str(edate)
                if not (_validate("%Y-%m-%d", sd) and _validate("%Y-%m-%d", ed)):
                    return Response({"error": "Invalid date range. Use YYYY-MM-DD for start_date and end_date"}, status=status.HTTP_400_BAD_REQUEST)
                if sd > ed:
                    sd, ed = ed, sd
                transfers = transfers.filter(request_date__gte=sd, request_date__lte=ed)
        except Exception as _date_err:
            return Response({"error": f"Failed to apply date filter: {_date_err}"}, status=status.HTTP_400_BAD_REQUEST)


        # Use only safe fields for ordering to avoid Oracle NCLOB issues
        transfers = transfers.order_by("-transaction_id")
        
        # Convert to list to avoid lazy evaluation issues with Oracle
        # Exclude TextField columns that become NCLOB in Oracle
        transfer_list = list(transfers.values(
            'transaction_id', 'transaction_date', 'amount', 'status', 
            'requested_by', 'user_id', 'request_date', 'code', 
            'gl_posting_status', 'approvel_1', 'approvel_2', 'approvel_3', 'approvel_4',
            'approvel_1_date', 'approvel_2_date', 'approvel_3_date', 'approvel_4_date',
            'status_level', 'attachment', 'fy', 'group_id', 'interface_id',
            'reject_group_id', 'reject_interface_id', 'approve_group_id', 'approve_interface_id',
            'report', 'type'
            # Excluding 'notes' field as it's TextField/NCLOB in Oracle
        ))
        
        # Manual pagination to avoid Oracle issues
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_data = transfer_list[start_idx:end_idx]
        
        return Response({
            'results': paginated_data,
            'count': len(transfer_list),
            'next': f"?page={page + 1}&page_size={page_size}" if end_idx < len(transfer_list) else None,
            'previous': f"?page={page - 1}&page_size={page_size}" if page > 1 else None
        })
class ListBudgetTransfer_approvels_View(APIView):
    """List budget transfers with pagination"""

    permission_classes = [IsAuthenticated]
    pagination_class = TransferPagination

    def get(self, request):
        code = request.query_params.get("code", None)
        date = request.data.get("date", None)
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)

        if code is None:
            code = "FAR"
        status_level_val = (
            request.user.user_level.level_order
            if request.user.user_level.level_order
            else 0
        )
        transfers = xx_BudgetTransfer.objects.filter(
            status_level=status_level_val, type=code,status= "pending"
        )
        
        if request.user.abilities.count() > 0:
            transfers = filter_budget_transfers_all_in_entities(transfers, request.user, 'approve')
        
        if code:
            transfers = transfers.filter(code__icontains=code)

        transfers = transfers.order_by("-request_date")

        # Paginate results
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(transfers, request, view=self)
        serializer = BudgetTransferSerializer(page, many=True)

        # Create a list of dictionaries with just the fields we want
        filtered_data = []
        for item in serializer.data:
            filtered_item = {
                "transaction_id": item.get("transaction_id"),
                "amount": item.get("amount"),
                "status": item.get("status"),
                "status_level": item.get("status_level"),
                "requested_by": item.get("requested_by"),
                "request_date": item.get("request_date"),
                "code": item.get("code"),
                "transaction_date": item.get("transaction_date"),
            }
            filtered_data.append(filtered_item)

        return paginator.get_paginated_response(filtered_data)
class ApproveBudgetTransferView(APIView):
    """Approve or reject budget transfer requests (admin only)"""

    permission_classes = [IsAuthenticated, IsAdmin]

    def put(self, request, transfer_id):
        try:
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)

            if transfer.status != "pending":
                return Response(
                    {"message": f"This transfer has already been {transfer.status}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            action = request.data.get("action")

            if action not in ["approve", "reject"]:
                return Response(
                    {"message": 'Invalid action. Use "approve" or "reject".'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            transfer.status = "approved" if action == "approve" else "rejected"

            current_level = transfer.status_level or 0
            next_level = current_level + 1

            if next_level <= 4:
                setattr(transfer, f"approvel_{next_level}", request.user.username)
                setattr(transfer, f"approvel_{next_level}_date", timezone.now())
                transfer.status_level = next_level

            transfer.save()

            return Response(
                {
                    "message": f"Budget transfer {transfer.status}.",
                    "data": BudgetTransferSerializer(transfer).data,
                }
            )

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"message": "Transfer not found."}, status=status.HTTP_404_NOT_FOUND
            )
class GetBudgetTransferView(APIView):
    """Get a specific budget transfer by ID"""

    permission_classes = [IsAuthenticated]

    def get(self, request, transfer_id):
        try:
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)

            # Check permissions: admin can see all, users can only see their own
            # if request.user.role != 'admin' and transfer.user_id != request.user.id:
            #     return Response(
            #         {'message': 'You do not have permission to view this transfer.'},
            #         status=status.HTTP_403_FORBIDDEN
            #     )
            # serializer = BudgetTransferSerializer(transfer)
            # return Response(serializer.data)
            data = {
                "transaction_id": transfer.transaction_id,
                "amount": transfer.amount,
                "status": transfer.status,
                "requested_by": transfer.requested_by,
                "description": transfer.notes,
            }

            return Response(data)

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"message": "Transfer not found."}, status=status.HTTP_404_NOT_FOUND
            )
class UpdateBudgetTransferView(APIView):
    """Update a budget transfer"""

    permission_classes = [IsAuthenticated]

    def put(self, request, transfer_id):

        try:

            transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)
             # Get transaction_id from the request
            transaction_id = request.data.get("transaction")
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)

            if transfer.status != "pending":
                return Response(
                    {
                        "message": f'Cannot upload files for transfer with status "{transfer.status}". Only pending transfers can have files uploaded.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not request.user.role == "admin" and transfer.user_id != request.user.id:

                return Response(
                    {"message": "You do not have permission to update this transfer."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if transfer.status != "pending":
                return Response(
                    {
                        "message": f'Cannot update transfer with status "{transfer.status}". Only pending transfers can be updated.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = BudgetTransferSerializer(
                transfer, data=request.data, partial=True
            )

            if serializer.is_valid():

                allowed_fields = [
                    "notes",
                    "description_x",
                    "amount",
                    "transaction_date",
                ]

                update_data = {}
                for field in allowed_fields:
                    if field in request.data:
                        update_data[field] = request.data[field]

                if not update_data:
                    return Response(
                        {"message": "No valid fields to update."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                for key, value in update_data.items():
                    setattr(transfer, key, value)

                transfer.save()

                return Response(
                    {
                        "message": "Budget transfer updated successfully.",
                        "data": BudgetTransferSerializer(transfer).data,
                    }
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"message": "Transfer not found."}, status=status.HTTP_404_NOT_FOUND
            )
class DeleteBudgetTransferView(APIView):
    """Delete a specific budget transfer by ID"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, transfer_id):
        try:
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)

            if transfer.status != "pending":
                return Response(
                    {
                        "message": f'Cannot delete transfer with status "{transfer.status}". Only pending transfers can be deleted.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if request.user.role != "admin" and transfer.user_id != request.user.id:
                return Response(
                    {"message": "You do not have permission to delete this transfer."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            transfer_code = transfer.code
            transfer.delete()

            return Response(
                {"message": f"Budget transfer {transfer_code} deleted successfully."},
                status=status.HTTP_200_OK,
            )

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"message": "Transfer not found."}, status=status.HTTP_404_NOT_FOUND
            )
class Adjdtranscationtransferapprovel_reject(APIView):
    """Submit ADJD transaction transfers for approval"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if we received valid data
        if not request.data:
            return Response(
                {
                    "error": "Empty data provided",
                    "message": "Please provide at least one transaction ID",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Convert single item to list for consistent handling
        items_to_process = []
        if isinstance(request.data, list):
            items_to_process = request.data
        else:
            # Handle single transaction case
            items_to_process = [request.data]
        results = []
        # Process each transaction
        for item in items_to_process:
            transaction_id = item.get("transaction_id")[0]
            decide = item.get("decide")[0]
            if item.get("reason") is not None:
                reson = item.get("reason")[0]
            # Validate required fields
            if not transaction_id:
                return Response(
                    {
                        "error": "transaction id is required",
                        "message": "Please provide transaction id",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if decide not in [2, 3]:
                return Response(
                    {
                        "error": "Invalid decision value",
                        "message": "Decision value must be 2 (approve) or 3 (reject)",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if decide == 3 and not reson:
                return Response(
                    {
                        "error": "Reason is required for rejection",
                        "message": "Please provide a reason for rejection",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                # Get the transfer record - use get() for single record
                trasncation = xx_BudgetTransfer.objects.get(
                    transaction_id=transaction_id
                )
                # Get the transfer type code
                code = trasncation.code.split("-")[0]
                # Handle approval flow based on transfer type
                if code == "FAR" or code == "AFR":
                    max_level = 4
                else:
                    max_level = 3
                # Update approval based on decision
                if decide == 2 and trasncation.status_level <= max_level:  # Approve
                    level = trasncation.status_level
                    # Set the appropriate approval fields
                    if level == 2:
                        trasncation.approvel_2 = request.user.username
                        trasncation.approvel_2_date = timezone.now()
                    elif level == 3:
                        trasncation.approvel_3 = request.user.username
                        trasncation.approvel_3_date = timezone.now()
                    elif level == 4:
                        trasncation.approvel_4 = request.user.username
                        trasncation.approvel_4_date = timezone.now()
                    if trasncation.status_level == max_level:
                        trasncation.status = "approved"
                    trasncation.status_level += 1
                elif decide == 3:  # Reject
                    # Record who rejected it at the current level
                    level = trasncation.status_level
                    if level == 2:
                        trasncation.approvel_2 = request.user.username
                        trasncation.approvel_2_date = timezone.now()
                    elif level == 3:
                        trasncation.approvel_3 = request.user.username
                        trasncation.approvel_3_date = timezone.now()
                    elif level == 4:
                        trasncation.approvel_4 = request.user.username
                        trasncation.approvel_4_date = timezone.now()
                    trasncation.status_level = -1
                    Reson_object = xx_BudgetTransferRejectReason.objects.create(
                        Transcation_id=trasncation,
                        reason_text=reson,
                        reject_by=request.user.username,
                    )
                    Reson_object.save()
                    trasncation.status = "rejected"
                # Save changes to the transfer
                trasncation.save()
                # Update pivot fund if final approval or rejection
                pivot_updates = []
                if (
                    max_level == trasncation.status_level and decide == 2
                ) or decide == 3:
                    trasfers = xx_TransactionTransfer.objects.filter(
                        transaction_id=transaction_id
                    )
                    for transfer in trasfers:
                        try:
                            # Extract the necessary data
                            item_cost_center = transfer.cost_center_code
                            item_account_code = transfer.account_code
                            from_center = transfer.from_center or 0
                            to_center = transfer.to_center or 0
                            # Update the pivot fund
                            update_result = update_pivot_fund(
                                item_cost_center,
                                item_account_code,
                                from_center,
                                to_center,
                                decide,
                            )
                            if update_result:
                                pivot_updates.append(update_result)
                        except Exception as e:
                            return Response(
                                {
                                    "error": "Error updating pivot fund",
                                    "message": str(e),
                                },
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            )
                        # Add the result for this transaction
                        results.append(
                            {
                                "transaction_id": transaction_id,
                                "status": "approved" if decide == 2 else "rejected",
                                "status_level": trasncation.status_level,
                                "pivot_updates": pivot_updates,
                            }
                        )
            except xx_BudgetTransfer.DoesNotExist:
                results.append(
                    {
                        "transaction_id": transaction_id,
                        "status": "error",
                        "message": f"Budget transfer not found",
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "transaction_id": transaction_id,
                        "status": "error",
                        "message": str(e),
                    }
                )

        # Return all results
        return Response(
            {"message": "Transfers processed", "results": results},
            status=status.HTTP_200_OK,
        )
class BudgetTransferFileUploadView(APIView):
    """Upload files for a budget transfer and store as BLOBs"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Check if the transfer exists
            transaction_id = request.data.get("transaction_id")
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)
            if transfer.status != "pending":
                return Response(
                    {
                        "message": f'Cannot upload files for transfer with status "{transfer.status}". Only pending transfers can have files uploaded.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if any files were provided
            if not request.FILES:
                return Response(
                    {
                        "error": "No files provided",
                        "message": "Please upload at least one file",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Process each uploaded file
            uploaded_files = []
            for file_key, uploaded_file in request.FILES.items():
                # Read the file data
                file_data = uploaded_file.read()

                # Create the attachment record
                attachment = xx_BudgetTransferAttachment.objects.create(
                    budget_transfer=transfer,
                    file_name=uploaded_file.name,
                    file_type=uploaded_file.content_type,
                    file_size=len(file_data),
                    file_data=file_data,
                )

                uploaded_files.append(
                    {
                        "attachment_id": attachment.attachment_id,
                        "file_name": attachment.file_name,
                        "file_type": attachment.file_type,
                        "file_size": attachment.file_size,
                        "upload_date": attachment.upload_date,
                    }
                )

            # Update the attachment flag on the budget transfer
            transfer.attachment = "Yes"
            transfer.save()

            return Response(
                {
                    "message": f"{len(uploaded_files)} files uploaded successfully",
                    "files": uploaded_files,
                },
                status=status.HTTP_201_CREATED,
            )

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {
                    "error": "Budget transfer not found",
                    "message": f"No budget transfer found with ID: {transaction_id}",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
class DeleteBudgetTransferAttachmentView(APIView):
    """Delete a specific file attachment from a budget transfer"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, transfer_id, attachment_id):
        try:
            # First, check if the budget transfer exists
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)
            if transfer.status != "pending":
                return Response(
                    {
                        "message": f'Cannot upload files for transfer with status "{transfer.status}". Only pending transfers can have files uploaded.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if user has permission to modify this transfer
            if not request.user.role == "admin" and transfer.user_id != request.user.id:
                return Response(
                    {
                        "message": "You do not have permission to modify attachments for this transfer."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Check if transfer is in editable state
            if transfer.status != "pending":
                return Response(
                    {
                        "message": f'Cannot modify attachments for transfer with status "{transfer.status}". Only pending transfers can be modified.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Find the specific attachment
            try:
                attachment = xx_BudgetTransferAttachment.objects.get(
                    attachment_id=attachment_id, budget_transfer=transfer
                )

                # Keep attachment details for response
                attachment_details = {
                    "attachment_id": attachment.attachment_id,
                    "file_name": attachment.file_name,
                }

                # Delete the attachment
                attachment.delete()

                # Check if this was the last attachment for this transfer
                remaining_attachments = xx_BudgetTransferAttachment.objects.filter(
                    budget_transfer=transfer
                ).exists()
                if not remaining_attachments:
                    transfer.attachment = "No"
                    transfer.save()

                return Response(
                    {
                        "message": f'File "{attachment_details["file_name"]}" deleted successfully',
                        "attachment_id": attachment_details["attachment_id"],
                    },
                    status=status.HTTP_200_OK,
                )

            except xx_BudgetTransferAttachment.DoesNotExist:
                return Response(
                    {
                        "error": "Attachment not found",
                        "message": f"No attachment found with ID {attachment_id} for this transfer",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {
                    "error": "Budget transfer not found",
                    "message": f"No budget transfer found with ID: {transfer_id}",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
class ListBudgetTransferAttachmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:

            transfer_id = request.query_params.get("transaction_id")
            # Retrieve the main budget transfer record
            transfer = xx_BudgetTransfer.objects.get(transaction_id=transfer_id)

            # Fetch related attachments
            attachments = xx_BudgetTransferAttachment.objects.filter(
                budget_transfer=transfer
            )

            # Build a simplified response
            data = []
            for attach in attachments:
                encoded_data = base64.b64encode(attach.file_data).decode("utf-8")
                data.append(
                    {
                        "attachment_id": attach.attachment_id,
                        "file_name": attach.file_name,
                        "file_type": attach.file_type,
                        "file_size": attach.file_size,
                        "file_data": encoded_data,  # base64-encoded
                        "upload_date": attach.upload_date,
                    }
                )

            return Response(
                {"transaction_id": transfer_id, "attachments": data},
                status=status.HTTP_200_OK,
            )
        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {"error": "Transfer not found"}, status=status.HTTP_404_NOT_FOUND
            )
class list_budget_transfer_reject_reason(APIView):
    """List all budget transfer reject reasons"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            reasons = xx_BudgetTransferRejectReason.objects.filter(
                Transcation_id=request.query_params.get("transaction_id")
            )
            data = []
            for reason in reasons:
                data.append(
                    {
                        "transaction_id": reason.Transcation_id.transaction_id,
                        "reason_text": reason.reason_text,
                        "created_at": reason.reject_date,
                        "rejected by": reason.reject_by,
                    }
                )
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class StaticDashboardView(APIView):
    """Optimized dashboard view for encrypted budget transfers"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get dashboard type from query params (default to 'smart')
            dashboard_type = request.query_params.get('type', 'smart')
            
            # Check if user wants to force refresh
            force_refresh = request.query_params.get('refresh', 'false').lower() == 'true'
            
            if force_refresh:
                # Only refresh when explicitly requested
                data = refresh_dashboard_data(dashboard_type)
                if data:
                    return Response(data, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {"error": "Failed to refresh dashboard data"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                # Always try to get existing cached data first
                if dashboard_type == 'all':
                    # Get all dashboard data (both smart and normal)
                    data = get_all_dashboard_data()
                    if data:
                        return Response(data, status=status.HTTP_200_OK)
                    else:
                        # Return empty structure if no data exists yet
                        return Response(
                            {
                                "message": "No dashboard data available yet. Data will be generated in background.",
                                "data": {}
                            }, 
                            status=status.HTTP_200_OK
                        )
                else:
                    # Get specific dashboard type (smart or normal)
                    data = get_saved_dashboard_data(dashboard_type)
                    if data:
                        return Response(data, status=status.HTTP_200_OK)
                    else:
                        # Return message if no cached data exists
                        return Response(
                            {
                                "message": f"No {dashboard_type} dashboard data available yet. Data will be generated in background.",
                                "data": {}
                            }, 
                            status=status.HTTP_200_OK
                        )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class DashboardBudgetTransferView(APIView):

    """Optimized dashboard view for encrypted budget transfers"""
    permission_classes = [IsAuthenticated]

    def get(self, request):

        try:
            # Get dashboard type from query params (default to 'smart')

            return_data={}
            dashboard_type = request.query_params.get('type', 'smart')
            force_refresh = request.query_params.get('refresh', 'false').lower() == 'true'




            DashBoard_filler_per_Project = request.query_params.get('DashBoard_filler_per_Project', None)

            start_time = time.time()
            print("Starting optimized normal dashboard calculation...")

            # PHASE 1: Database-level counting and aggregations
            count_start = time.time()

            # Get all transfers with minimal data loading
            transfers_queryset = xx_BudgetTransfer.objects.only(
            'code', 'status', 'status_level', 'request_date'
            )
            # if request.user.abilities.count() > 0:
            print(len(transfers_queryset))
            transfers_queryset = filter_budget_transfers_all_in_entities(transfers_queryset, request.user, 'edit',dashboard_filler_per_project=DashBoard_filler_per_Project)
            print(len(transfers_queryset))

            if dashboard_type=="normal"  or dashboard_type=="all":
                # Use database aggregations for counting
                try:

                    total_count = transfers_queryset.count()

                    # Count by status using database aggregation
                    status_counts = transfers_queryset.aggregate(
                        approved=Count('transaction_id', filter=Q(status='approved')),
                        rejected=Count('transaction_id', filter=Q(status='rejected')),
                        pending=Count('transaction_id', filter=Q(status='pending'))
                    )

                    # Count by status level using database aggregation
                    level_counts = transfers_queryset.aggregate(
                        level1=Count('transaction_id', filter=Q(status_level=1)),
                        level2=Count('transaction_id', filter=Q(status_level=2)),
                        level3=Count('transaction_id', filter=Q(status_level=3)),
                        level4=Count('transaction_id', filter=Q(status_level=4))
                    )

                    # Count by code prefix using database functions
                    code_counts = transfers_queryset.aggregate(
                        far=Count('transaction_id', filter=Q(code__istartswith='FAR')),
                        afr=Count('transaction_id', filter=Q(code__istartswith='AFR')),
                        fad=Count('transaction_id', filter=Q(code__istartswith='FAD'))
                    )

                    # Get request dates efficiently (only non-null dates)
                    request_dates = list(
                        transfers_queryset.filter(request_date__isnull=False)
                        .values_list('request_date', flat=True)
                        .order_by('-request_date')[:1000]  # Limit to recent 1000 for performance
                    )

                    # Convert datetime objects to ISO format strings for JSON serialization
                    request_dates_iso = [date.isoformat() for date in request_dates]

                    print(f"Database counting completed in {time.time() - count_start:.2f}s")

                    # PHASE 2: Format response data
                    data = {
                        "total_transfers": total_count,
                        "total_transfers_far": code_counts['far'],
                        "total_transfers_afr": code_counts['afr'],
                        "total_transfers_fad": code_counts['fad'],
                        "approved_transfers": status_counts['approved'],
                        "rejected_transfers": status_counts['rejected'],
                        "pending_transfers": status_counts['pending'],
                        "pending_transfers_by_level": {
                            "Level1": level_counts['level1'],
                            "Level2": level_counts['level2'],
                            "Level3": level_counts['level3'],
                            "Level4": level_counts['level4'],
                        },
                        "request_dates": request_dates_iso,
                        "performance_metrics": {
                            "total_processing_time": round(time.time() - start_time, 2),
                            "counting_time": round(time.time() - count_start, 2),
                            "total_records_processed": total_count,
                            "request_dates_retrieved": len(request_dates_iso)
                        }
                    }

                    print(f"Total optimized processing time: {time.time() - start_time:.2f}s")
                    print(f"Processed {total_count} transfers")

                    # Save dashboard data
                    save_start = time.time()
                    try:
                        # Ensure a local container exists to store dashboard data
                        return_data['normal'] = data

                        # If only normal dashboard is requested, return now.
                        if dashboard_type == "normal":
                            return Response(return_data, status=status.HTTP_200_OK)
                    except Exception as e:
                        print(f"Error occurred while saving dashboard data: {str(e)}")
                except Exception as e:
                    print(f"Error occurred while saving dashboard data: {str(e)}")
            if dashboard_type=="smart" or dashboard_type=="all":
                try:
                    start_time = time.time()

                    print("Starting optimized smart dashboard calculation...")
                    if DashBoard_filler_per_Project :
                        print(f"Filters applied: cost_center={DashBoard_filler_per_Project}")
                    # PHASE 1: Database-level aggregations for approved transfers
                    aggregation_start = time.time()
                    
                    # Build base queryset with optimized filtering
                    base_queryset = xx_TransactionTransfer.objects.select_related('transaction').filter(
                        transaction__status="approved"
                    )
                    
                    # Apply additional filters if provided
                    if DashBoard_filler_per_Project:
                        base_queryset = base_queryset.filter(cost_center_code=DashBoard_filler_per_Project)
                    
                    # Aggregate by cost center code (single database query)
                    cost_center_totals = list(base_queryset.values('cost_center_code').annotate(
                        total_from_center=Sum('from_center'),
                        total_to_center=Sum('to_center')
                    ).order_by('cost_center_code'))

                    # Aggregate by account code (single database query)
                    account_code_totals = list(base_queryset.values('account_code').annotate(
                        total_from_center=Sum('from_center'),
                        total_to_center=Sum('to_center')
                    ).order_by('account_code'))

                    # Aggregate by combination of cost center and account code (single database query)
                    all_combinations = list(base_queryset.values('cost_center_code', 'account_code').annotate(
                        total_from_center=Sum('from_center'),
                        total_to_center=Sum('to_center')
                    ).order_by('cost_center_code', 'account_code'))

                    # Get filtered individual records if filters are applied
                    if DashBoard_filler_per_Project:
                        filtered_combinations = list(base_queryset.values(
                            'cost_center_code', 'account_code', 'from_center', 'to_center'
                        ))
                    else:
                        # If no filters, use aggregated data to avoid large result sets
                        filtered_combinations = all_combinations

                    print(f"Database aggregations completed in {time.time() - aggregation_start:.2f}s")

                    # PHASE 2: Format response data
                    format_start = time.time()
                    
                    # Convert Decimal to float for JSON serialization
                    for item in cost_center_totals:
                        item['total_from_center'] = float(item['total_from_center'] or 0)
                        item['total_to_center'] = float(item['total_to_center'] or 0)

                    for item in account_code_totals:
                        item['total_from_center'] = float(item['total_from_center'] or 0)
                        item['total_to_center'] = float(item['total_to_center'] or 0)

                    for item in all_combinations:
                        item['total_from_center'] = float(item['total_from_center'] or 0)
                        item['total_to_center'] = float(item['total_to_center'] or 0)

                    # Convert filtered combinations
                    for item in filtered_combinations:
                        if 'from_center' in item:  # Individual records
                            item['from_center'] = float(item['from_center'] or 0)
                            item['to_center'] = float(item['to_center'] or 0)

                    print(f"Data formatting completed in {time.time() - format_start:.2f}s")

                    # Prepare final response
                    data = {
                        "filtered_combinations": filtered_combinations,
                        "cost_center_totals": cost_center_totals,
                        "account_code_totals": account_code_totals,
                        "all_combinations": all_combinations,
                        "applied_filters": {
                            "cost_center_code": DashBoard_filler_per_Project,
                        },
                        "performance_metrics": {
                            "total_processing_time": round(time.time() - start_time, 2),
                            "aggregation_time": round(time.time() - aggregation_start, 2),
                            "cost_center_groups": len(cost_center_totals),
                            "account_code_groups": len(account_code_totals),
                            "total_combinations": len(all_combinations)
                        }
                    }

                    print(f"Total optimized processing time: {time.time() - start_time:.2f}s")
                    print(f"Found {len(cost_center_totals)} cost centers, {len(account_code_totals)} account codes")

                    # Save dashboard data
                    save_start = time.time()
                    try:
                        return_data['smart'] = data
                        # If only smart dashboard is requested, return now.
                        if dashboard_type == "smart":
                            return Response(return_data, status=status.HTTP_200_OK)
                    except Exception as save_error:
                        print(f"Error saving dashboard data: {save_error}")
                        return data


                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        return Response(
                            {"error": str(e)}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                except Exception as e:
                    print(f"Error processing dashboard data: {e}")
                    return Response(
                        {"error": str(e)}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            # If we reach here, and we have collected one or more sections (e.g., type=all), return them.
            if return_data:
                return Response(return_data, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        



### mobile version #####

class ListBudgetTransfer_approvels_MobileView(APIView):
    """List budget transfers with pagination"""

    permission_classes = [IsAuthenticated]
    pagination_class = TransferPagination

    def get(self, request):
        code = request.query_params.get("code", None)
        date = request.data.get("date", None)
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)
        
        if code is None:
            code = "FAR"
        status_level_val = (
            request.user.user_level.level_order
            if request.user.user_level.level_order
            else 0
        )
        transfers = xx_BudgetTransfer.objects.filter(
            status_level=status_level_val, type=code,status= "pending"
        )
        
        if request.user.abilities.count() > 0:
            transfers = filter_budget_transfers_all_in_entities(transfers, request.user, 'approve')
        
        if code:
            transfers = transfers.filter(code__icontains=code)

        transfers = transfers.order_by("-request_date")
        # Return all results without pagination
        serializer = BudgetTransferSerializer(transfers, many=True)

        # Create a list of dictionaries with just the fields we want
        filtered_data = []
        for item in serializer.data:
            filtered_item = {
                "transaction_id": item.get("transaction_id"),
                "amount": item.get("amount"),
                "status": item.get("status"),
                "status_level": item.get("status_level"),
                "requested_by": item.get("requested_by"),
                "request_date": item.get("request_date"),
                "code": item.get("code"),
                "transaction_date": item.get("transaction_date"),
            }
            filtered_data.append(filtered_item)

        return Response(filtered_data, status=status.HTTP_200_OK)
