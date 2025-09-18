import rest_framework
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import xx_TransactionTransfer
from account_and_entitys.models import XX_Entity, XX_PivotFund, XX_ACCOUNT_ENTITY_LIMIT
from budget_management.models import xx_BudgetTransfer
from .serializers import TransactionTransferSerializer
from decimal import Decimal
from django.db.models import Sum
from public_funtion.update_pivot_fund import update_pivot_fund
from django.utils import timezone
from user_management.models import xx_notification
import pandas as pd
import io
import os
import base64
import time
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from pathlib import Path
from django.conf import settings
from test_upload_fbdi.journal_template_manager import (
    create_sample_journal_data,
    create_journal_from_scratch,
)
from test_upload_fbdi.upload_soap_fbdi import (
    b64_csv,
    build_soap_envelope,
    upload_fbdi_to_oracle,
)
from account_and_entitys.utils import get_oracle_report_data
from test_upload_fbdi.utility.creat_and_upload import submint_journal_and_upload 
from test_upload_fbdi.utility.submit_budget_and_upload import submit_budget_and_upload
from test_upload_fbdi.automatic_posting import submit_automatic_posting
def validate_transaction(data, code=None):
    """
    Validate ADJD transaction transfer data against 10 business rules
    Returns a list of validation errors or empty list if valid
    """
    errors = []

    # Validation 1: Check required fields
    required_fields = [
        "from_center",
        "to_center",
        "approved_budget",
        "available_budget",
        "encumbrance",
        "actual",
        "cost_center_code",
        "account_code",
        "project_code",
    ]
    if data["from_center"] == "":
        data["from_center"] = 0
    if data["to_center"] == "":
        data["to_center"] = 0
    if data["approved_budget"] == "":
        data["approved_budget"] = 0
    if data["available_budget"] == "":
        data["available_budget"] = 0
    if data["encumbrance"] == "":
        data["encumbrance"] = 0
    if data["actual"] == "":
        data["actual"] = 0

    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(f"{field} is required")

    # If basic required fields are missing, stop further validation
    if errors:
        return errors

    # Validation 2: from_center or to_center must be positive
    if code[0:3] != "AFR":
        if Decimal(data["from_center"]) < 0:
            errors.append("from amount must be positive")

        if Decimal(data["to_center"]) < 0:
            errors.append("to amount must be positive")

    # Validation 3: Check if both from_center and to_center are positive

    if Decimal(data["from_center"]) > 0 and Decimal(data["to_center"]) > 0:

        errors.append("Can't have value in both from and to at the same time")

    # Validation 4: Check if available_budget > from_center
    if code[0:3] != "AFR":
        if Decimal(data["from_center"]) > Decimal(data["available_budget"]):
            errors.append(" from value must be less or equal available_budget value")

    # Validation 5: Check for duplicate transfers (same transaction, from_account, to_account)
    existing_transfers = xx_TransactionTransfer.objects.filter(
        transaction=data["transaction_id"],
        cost_center_code=data["cost_center_code"],
        account_code=data["account_code"],
        project_code=data["project_code"],
    )

    # If we're validating an existing record, exclude it from the duplicate check
    if "transfer_id" in data and data["transfer_id"]:
        existing_transfers = existing_transfers.exclude(transfer_id=data["transfer_id"])

    if existing_transfers.exists():
        duplicates = [f"ID: {t.transfer_id}" for t in existing_transfers[:3]]
        errors.append(
            f"Duplicate transfer for account code {data['account_code']} and project code {data['project_code']} and cost center {data['cost_center_code']} (Found: {', '.join(duplicates)})"
        )

    return errors


def validate_transcation_transfer(data, code=None, errors=None):
    # Validation 1: Check for fund is available if not then no combination code
    existing_code_combintion = XX_PivotFund.objects.filter(
        entity=data["cost_center_code"],
        account=data["account_code"],
        project=data["project_code"],
    )
    if not existing_code_combintion.exists():
        errors.append(
            f"Code combination not found for {data['cost_center_code']} and {data['project_code']} and {data['account_code']}"
        )
    print(
        "existing_code_combintion",
        type(data["cost_center_code"]),
        ":",
        type(data["project_code"]),
        ":",
        type(data["account_code"]),
    )
    # Validation 2: Check if is allowed to make trasfer using this cost_center_code and account_code
    allowed_to_make_transfer = XX_ACCOUNT_ENTITY_LIMIT.objects.filter(
        entity_id=str(data["cost_center_code"]),
        account_id=str(data["account_code"]),
        project_id=str(data["project_code"]),
    ).first()
    print("allowed_to_make_transfer", allowed_to_make_transfer)

    # Check if no matching record found
    if allowed_to_make_transfer is not None:
        # Check transfer permissions if record exists
        if allowed_to_make_transfer.is_transer_allowed == "No":
            errors.append(
                f"Not allowed to make transfer for {data['cost_center_code']} and {data['project_code']} and {data['account_code']} according to the rules"
            )
        elif allowed_to_make_transfer.is_transer_allowed == "Yes":
            if data["from_center"] > 0:
                if allowed_to_make_transfer.is_transer_allowed_for_source != "Yes":
                    errors.append(
                        f"Not allowed to make transfer for {data['cost_center_code']} and {data['project_code']} and {data['account_code']} according to the rules (can't transfer from this account)"
                    )
            if data["to_center"] > 0:
                if allowed_to_make_transfer.is_transer_allowed_for_target != "Yes":
                    errors.append(
                        f"Not allowed to make transfer for {data['cost_center_code']} and {data['project_code']} and {data['account_code']} according to the rules (can't transfer to this account)"
                    )
    return errors


class TransactionTransferCreateView(APIView):
    """Create new transaction transfers (single or batch)"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if the data is a list/array or single object
        if isinstance(request.data, list):
            # Handle array of transfers
            if not request.data:
                return Response(
                    {
                        "error": "Empty data provided",
                        "message": "Please provide at least one transfer",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get transaction_id from the first item for batch operations
            transaction_id = request.data[0].get("transaction")
            if not transaction_id:
                return Response(
                    {
                        "error": "transaction_id is required",
                        "message": "You must provide a transaction_id for each transfer",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Delete all existing transfers for this transaction
            xx_TransactionTransfer.objects.filter(transaction=transaction_id).delete()

            # Process the new transfers
            results = []
            for index, transfer_data in enumerate(request.data):
                # Make sure all items have the same transaction ID
                if transfer_data.get("transaction") != transaction_id:
                    results.append(
                        {
                            "index": index,
                            "error": "All transfers must have the same transaction_id",
                            "data": transfer_data,
                        }
                    )
                    continue

                # Validate and save each transfer
                serializer = TransactionTransferSerializer(data=transfer_data)
                if serializer.is_valid():
                    transfer = serializer.save()
                    results.append(serializer.data)
                    print(f"Transfer {index} created: {transfer}")
                else:
                    print(
                        f"Validation errors for transfer at index {index}: {serializer.errors}"
                    )
                    results.append(
                        {
                            "index": index,
                            "error": serializer.errors,
                            "data": transfer_data,
                        }
                    )

            return Response(results, status=status.HTTP_207_MULTI_STATUS)
        else:
            # Handle single transfer
            transaction_id = request.data.get("transaction")
            if not transaction_id:
                return Response(
                    {
                        "error": "transaction_id is required",
                        "message": "You must provide a transaction_id to create an transaction transfer",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Delete all existing transfers for this transaction for single item operations
            xx_TransactionTransfer.objects.filter(transaction=transaction_id).delete()

            # Validate with serializer and create new transfer

            transfer_data = request.data
            from_center = transfer_data.get("from_center")
            if from_center is None or str(from_center).strip() == "":
                from_center = 0
            to_center = transfer_data.get("to_center")
            if to_center is None or str(to_center).strip() == "":
                to_center = 0
            cost_center_code = transfer_data.get("cost_center_code")
            account_code = transfer_data.get("account_code")
            project_code = transfer_data.get("project_code")
            transfer_id = transfer_data.get("transfer_id")
            approved_budget = transfer_data.get("approved_budget")
            available_budget = transfer_data.get("available_budget")
            encumbrance = transfer_data.get("encumbrance")
            actual = transfer_data.get("actual")

            # Prepare data for validation function
            validation_data = {
                "transaction_id": transaction_id,
                "from_center": from_center,
                "to_center": to_center,
                "approved_budget": approved_budget,
                "available_budget": available_budget,
                "encumbrance": encumbrance,
                "actual": actual,
                "cost_center_code": cost_center_code,
                "account_code": account_code,
                "project_code": project_code,
                "transfer_id": transfer_id,  # Fixed: was using 'transfer_id' instead of 'id'
            }

            serializer = TransactionTransferSerializer(data=validation_data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                serializer.save()
                print(
                    f"Validation errors for transfer at index {index}: {serializer.errors}"
                )
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransactionTransferListView(APIView):
    """List transaction transfers for a specific transaction"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        transaction_id = request.query_params.get("transaction")
        print(f"Transaction ID: {transaction_id}")
        if not transaction_id:
            return Response(
                {
                    "error": "transaction_id is required",
                    "message": "Please provide a transaction ID to retrieve related transfers",
                },
                status=rest_framework.status.HTTP_400_BAD_REQUEST,
            )

        transaction_object = xx_BudgetTransfer.objects.get(
            transaction_id=transaction_id
        )
        if not transaction_object:
            return Response(
                {
                    "error": "transaction not found",
                    "message": f"No transaction found with ID: {transaction_id}",
                },
                status=rest_framework.status.HTTP_404_NOT_FOUND,
            )
        status = False
        if transaction_object.code[0:3] != "FAD":

            if transaction_object.status_level and transaction_object.status_level < 1:
                status = "is rejected"
            elif (
                transaction_object.status_level and transaction_object.status_level == 1
            ):
                status = "not yet sent for approval"
            elif (
                transaction_object.status_level and transaction_object.status_level == 4
            ):
                status = "approved"
            else:
                status = "waiting for approval"
        else:
            if transaction_object.status_level and transaction_object.status_level < 1:
                status = "is rejected"
            elif (
                transaction_object.status_level and transaction_object.status_level == 3
            ):
                status = "approved"
            elif (
                transaction_object.status_level and transaction_object.status_level == 1
            ):
                status = "not yet sent for approval"
            else:
                status = "waiting for approval"

        transfers = xx_TransactionTransfer.objects.filter(transaction=transaction_id)
        serializer = TransactionTransferSerializer(transfers, many=True)

        for transfer in transfers:
            result = get_oracle_report_data(
                segment1=transfer.cost_center_code,
                segment2=transfer.account_code,
                segment3=transfer.project_code,
            )
            data = result["data"]

            if data and len(data) > 0:
                record = data[0]
                transfer.available_budget = record["funds_available_asof"]
                transfer.approved_budget = record["budget_ytd"]
                transfer.encumbrance = record["encumbrance_ytd"]
                transfer.actual = record["actual_ytd"]
                transfer.budget_adjustments = record["budget_adjustments"]
                transfer.commitments = record["commitments"]
                transfer.expenditures = record["expenditures"]
                transfer.initial_budget = record["initial_budget"]
                transfer.obligations = record["obligations"]
                transfer.other_consumption = record["other_consumption"]
            else:
                # No data found, set default values
                transfer.available_budget = 0.0
                transfer.approved_budget = 0.0
                transfer.encumbrance = 0.0
                transfer.actual = 0.0
                transfer.budget_adjustments = 0.0
                transfer.commitments = 0.0
                transfer.expenditures = 0.0
                transfer.initial_budget = 0.0
                transfer.obligations = 0.0
                transfer.other_consumption = 0.0
                

            transfer.save()

        # Create response with validation for each transfer
        response_data = []
        for transfer_data in serializer.data:
            from_center_val = transfer_data.get("from_center", 0)
            from_center = (
                float(from_center_val) if from_center_val not in [None, ""] else 0.0
            )
            to_center = float(transfer_data.get("to_center", 0))
            cost_center_code = transfer_data.get("cost_center_code")
            account_code = transfer_data.get("account_code")
            project_code = transfer_data.get("project_code")
            transfer_id = transfer_data.get("transfer_id")
            approved_budget = float(transfer_data.get("approved_budget", 0))
            available_budget = float(transfer_data.get("available_budget", 0))
            encumbrance = float(transfer_data.get("encumbrance", 0))
            actual = float(transfer_data.get("actual", 0))

            # Prepare data for validation function
            validation_data = {
                "transaction_id": transaction_id,
                "from_center": from_center,
                "to_center": to_center,
                "approved_budget": approved_budget,
                "available_budget": available_budget,
                "encumbrance": encumbrance,
                "actual": actual,
                "cost_center_code": cost_center_code,
                "account_code": account_code,
                "project_code": project_code,
                "transfer_id": transfer_id,  # Fixed: was using 'transfer_id' instead of 'id'
            }

            # Validate the transfer
            validation_errors = validate_transaction(
                validation_data, code=transaction_object.code
            )
            # validation_errors = validate_transcation_transfer(
            #     validation_data, code=transaction_object.code, errors=validation_errors
            # )
            # Add validation results to the transfer data
            transfer_result = transfer_data.copy()
            if validation_errors:
                transfer_result["validation_errors"] = validation_errors

            response_data.append(transfer_result)

        # Also add transaction-wide validation summary

        all_related_transfers = xx_TransactionTransfer.objects.filter(
            transaction=transaction_id
        )

        if all_related_transfers.exists():
            from_center_values = all_related_transfers.values_list(
                "from_center", flat=True
            )
            to_center_values = all_related_transfers.values_list("to_center", flat=True)
            total_from_center = sum(
                float(value) if value not in [None, ""] else 0
                for value in from_center_values
            )
            total_to_center = sum(
                float(value) if value not in [None, ""] else 0
                for value in to_center_values
            )

            if total_from_center == total_to_center:
                transaction_object.amount = total_from_center
                xx_BudgetTransfer.objects.filter(pk=transaction_id).update(
                    amount=total_from_center
                )

            if transaction_object.code[0:3] == "AFR":
                summary = {
                    "transaction_id": transaction_id,
                    "total_transfers": len(response_data),
                    "total_from": total_from_center,
                    "total_to": total_to_center,
                    "balanced": True,
                    "status": status,
                    "period": transaction_object.transaction_date + str(-25),
                }
            else:
                summary = {
                    "transaction_id": transaction_id,
                    "total_transfers": len(response_data),
                    "total_from": total_from_center,
                    "total_to": total_to_center,
                    "balanced": total_from_center == total_to_center,
                    "status": status,
                    "period": transaction_object.transaction_date + str(-25),
                }

            status = {"status": status}
            return Response(
                {"summary": summary, "transfers": response_data, "status": status}
            )
        else:
            summary = {
                "transaction_id": transaction_id,
                "total_transfers": 0,
                "total_from": 0,
                "total_to": 0,
                "balanced": True,
                "status": status,
                "period": transaction_object.transaction_date + str(-25),
            }
            status = {"status": status}
            return Response(
                {"summary": summary, "transfers": response_data, "status": status}
            )


class TransactionTransferDetailView(APIView):
    """Retrieve a specific transaction transfer"""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            transfer = xx_TransactionTransfer.objects.get(pk=pk)
            serializer = TransactionTransferSerializer(transfer)
            return Response(serializer.data)
        except xx_TransactionTransfer.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class TransactionTransferUpdateView(APIView):
    """Update an transaction transfer"""

    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        try:

            transfer = xx_TransactionTransfer.objects.get(pk=pk)

            # First validate with serializer
            serializer = TransactionTransferSerializer(transfer, data=request.data)
            if serializer.is_valid():
                # Save the data
                serializer.save()
                # Return the saved data without validation errors
                return Response(serializer.data)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except xx_TransactionTransfer.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class TransactionTransferDeleteView(APIView):
    """Delete an transaction transfer"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            transfer = xx_TransactionTransfer.objects.get(pk=pk)
            transfer.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except xx_TransactionTransfer.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class transcationtransferSubmit(APIView):
    """Submit transaction transfers for approval"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if we received a list or a single transaction ID
        print(f"Received data: {request.data}")

        if isinstance(request.data, dict):
            # Handle dictionary input for a single transaction
            print(f"Received dictionary data")
            if not request.data:
                return Response(
                    {
                        "error": "Empty data provided",
                        "message": "Please provide transaction data",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            transaction_id = request.data.get("transaction")

            if not transaction_id:
                return Response(
                    {
                        "error": "transaction id is required",
                        "message": "Please provide transaction id",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            pivot_updates = []

            try:
                # For dictionary input, get transfers from the database
                transfers = xx_TransactionTransfer.objects.filter(
                    transaction=transaction_id
                )
                code = xx_BudgetTransfer.objects.get(transaction_id=transaction_id).code
                print(f"Transfers found: {transfers.count()}")
                if len(transfers) < 2 and code[0:3] != "AFR":
                    return Response(
                        {
                            "error": "Not enough transfers",
                            "message": f"At least 2 transfers are required for transaction ID: {transaction_id}",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                for transfer in transfers:
                    if code[0:3] != "AFR":
                        if transfer.from_center is None or transfer.from_center <= 0:
                            if transfer.to_center is None or transfer.to_center <= 0:
                                return Response(
                                    {
                                        "error": "Invalid transfer amounts",
                                        "message": f"Each transfer must have a positive from_center or to_center value. Transfer ID {transfer.transfer_id} has invalid values.",
                                    },
                                    status=status.HTTP_400_BAD_REQUEST,
                                )
                        if transfer.from_center > 0 and transfer.to_center > 0:
                            return Response(
                                {
                                    "error": "Invalid transfer amounts",
                                    "message": f"Each transfer must have either from_center or to_center as positive, not both. Transfer ID {transfer.transfer_id} has both values positive.",
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    else:
                        if transfer.to_center <= 0:
                            return Response(
                                {
                                    "error": "Invalid transfer amounts",
                                    "message": f"transfer must have to_center as positive. Transfer ID {transfer.transfer_id}",
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    print(
                        f"Transfer ID: {transfer.transfer_id}, From Center: {transfer.from_center}, To Center: {transfer.to_center}, Cost Center Code: {transfer.cost_center_code}, Account Code: {transfer.account_code}"
                    )
                # Check if transfers exist
                if not transfers.exists():
                    return Response(
                        {
                            "error": "No transfers found",
                            "message": f"No transfers found for transaction ID: {transaction_id}",
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )

                if code[0:3] != "AFR":
                    csv_upload_result,result=submint_journal_and_upload(transfers=transfers,transaction_id=transaction_id,type="submit")
                    time.sleep(90)
                    submit_automatic_posting("300000288873799")
                    response_data = {
                    "message": "Transfers submitted for approval successfully",
                    "transaction_id": transaction_id,
                    "pivot_updates": pivot_updates,
                    "journal_file": result if result else None,
                     }
                    if csv_upload_result:
                        response_data["fbdi_upload"] = csv_upload_result

                else:
                    response_data = {
                        "message": "Transfers submitted for approval successfully",
                        "transaction_id": transaction_id,
                        "pivot_updates": pivot_updates,
                        "journal_file": None,
                }

                    # csv_upload_result,result=submit_budget_and_upload(transfers=transfers,transaction_id=transaction_id)

                budget_transfer = xx_BudgetTransfer.objects.get(pk=transaction_id)
                budget_transfer.status = "submitted"
                budget_transfer.status_level = 2
                budget_transfer.save()

                # user_submit=xx_notification()
                # user_submit.create_notification(user=request.user,message=f"you have submited the trasnation {transaction_id} secessfully ")

                # Prepare response data
                # response_data = {
                #     "message": "Transfers submitted for approval successfully",
                #     "transaction_id": transaction_id,
                #     "pivot_updates": pivot_updates,
                #     "journal_file": result if result else None,
                # }

                # Add FBDI upload results if available
                # if csv_upload_result:
                #     response_data["fbdi_upload"] = csv_upload_result

                # Return success response here, inside the try block
                return Response(response_data, status=status.HTTP_200_OK)

            except xx_BudgetTransfer.DoesNotExist:
                return Response(
                    {
                        "error": "Budget transfer not found",
                        "message": f"No budget transfer found for ID: {transaction_id}",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            except Exception as e:
                return Response(
                    {"error": "Error processing transfers", "message": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )


class transcationtransfer_Reopen(APIView):
    """Submit transaction transfers for approval"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if we received a list or a single transaction ID
        if not request.data:
            return Response(
                {
                    "error": "Empty data provided",
                    "message": "Please provide at least one transaction ID",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        transaction_id = request.data.get("transaction")
        action = request.data.get("action")

        if not transaction_id:
            return Response(
                {
                    "error": "transaction id is required",
                    "message": "Please provide transaction id",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get a single object instead of a QuerySet
            transaction = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)

            if transaction.status_level and transaction.status_level < 3:  # Must be 1:
                if action == "reopen":
                    # Update the single object
                    transaction.approvel_1 = None
                    transaction.approvel_2 = None
                    transaction.approvel_3 = None
                    transaction.approvel_4 = None
                    transaction.approvel_1_date = None
                    transaction.approvel_2_date = None
                    transaction.approvel_3_date = None
                    transaction.approvel_4_date = None
                    transaction.status = "pending"
                    transaction.status_level = 1
                    transaction.save()

                    return Response(
                        {
                            "message": "transaction re-opened successfully",
                            "transaction_id": transaction_id,
                        },
                        status=status.HTTP_200_OK,
                    )
            else:
                return Response(
                    {
                        "error": "transaction is not activated or not yet sent for approval",
                        "message": f"transaction {transaction_id} does not need to be re-opened",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except xx_BudgetTransfer.DoesNotExist:
            return Response(
                {
                    "error": "Transaction not found",
                    "message": f"No budget transfer found with ID: {transaction_id}",
                },
                status=status.HTTP_404_NOT_FOUND,
            )


class TransactionTransferExcelUploadView(APIView):
    """Upload Excel file to create transaction transfers"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if file was uploaded

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

        if "file" not in request.FILES:
            return Response(
                {"error": "No file uploaded", "message": "Please upload an Excel file"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the file from the request
        print("enter")
        excel_file = request.FILES["file"]
        print("took file")

        # Check if it's an Excel file
        if not excel_file.name.endswith((".xls", ".xlsx")):
            return Response(
                {
                    "error": "Invalid file format",
                    "message": "Please upload a valid Excel file (.xls or .xlsx)",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not transaction_id:
            return Response(
                {
                    "error": "transaction_id is required",
                    "message": "You must provide a transaction_id for the Excel import",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Read Excel file
            df = pd.read_excel(excel_file)

            # Validate required columns
            required_columns = [
                "cost_center_code",
                "account_code",
                "project_code",
                "from_center",
                "to_center",
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                return Response(
                    {
                        "error": "Missing columns in Excel file",
                        "message": f'The following columns are missing: {", ".join(missing_columns)}',
                        "required_columns": required_columns,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Delete existing transfers for this transaction
            # xx_TransactionTransfer.objects.filter(transaction=transaction_id).delete()

            # Process Excel data
            created_transfers = []
            errors = []
            print(df["cost_center_code"])
            print(df["account_code"])
            print(df["project_code"])

            for index, row in df.iterrows():
                try:
                    # Create transfer data dictionary
                    transfer_data = {
                        "transaction": transaction_id,
                        "cost_center_code": str(row["cost_center_code"]),
                        "project_code": str(row["project_code"]),
                        "account_code": str(row["account_code"]),
                        "from_center": (
                            float(row["from_center"])
                            if not pd.isna(row["from_center"])
                            else 0
                        ),
                        "to_center": (
                            float(row["to_center"])
                            if not pd.isna(row["to_center"])
                            else 0
                        ),
                        # Set default values for other required fields
                        "approved_budget": 0,
                        "available_budget": 0,
                        "encumbrance": 0,
                        "actual": 0,
                    }

                    # Validate and save
                    serializer = TransactionTransferSerializer(data=transfer_data)
                    if serializer.is_valid():
                        transfer = serializer.save()
                        created_transfers.append(serializer.data)
                    else:
                        errors.append(
                            {
                                "row": index
                                + 2,  # +2 because Excel is 1-indexed and there's a header row
                                "error": serializer.errors,
                                "data": transfer_data,
                            }
                        )
                except Exception as row_error:
                    errors.append(
                        {
                            "row": index + 2,
                            "error": str(row_error),
                            "data": row.to_dict(),
                        }
                    )

            # Return results
            response_data = {
                "message": f"Processed {len(created_transfers) + len(errors)} rows from Excel file",
                "created": created_transfers,
                "created_count": len(created_transfers),
                "errors": errors,
                "error_count": len(errors),
            }

            if len(errors) > 0 and len(created_transfers) == 0:
                # All items failed
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            elif len(errors) > 0:
                # Partial success
                return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
            else:
                # Complete success
                return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": "Error processing Excel file", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
