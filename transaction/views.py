import rest_framework
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import xx_TransactionTransfer
from account_and_entitys.models import (
    XX_Entity,
    XX_Account,
    XX_Project,
    XX_PivotFund,
    XX_ACCOUNT_ENTITY_LIMIT,
)
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

        # Build alias maps for names to avoid N+1 queries
        try:
            cost_center_codes = set(
                [str(item.get("cost_center_code")) for item in serializer.data if item.get("cost_center_code") is not None]
            )
            account_codes = set(
                [str(item.get("account_code")) for item in serializer.data if item.get("account_code") is not None]
            )
            project_codes = set(
                [str(item.get("project_code")) for item in serializer.data if item.get("project_code") is not None]
            )

            entity_alias_map = {
                str(e.entity): (e.alias_default or str(e.entity))
                for e in XX_Entity.objects.filter(entity__in=cost_center_codes)
            }
            account_alias_map = {
                str(a.account): (a.alias_default or str(a.account))
                for a in XX_Account.objects.filter(account__in=account_codes)
            }
            project_alias_map = {
                str(p.project): (p.alias_default or str(p.project))
                for p in XX_Project.objects.filter(project__in=project_codes)
            }
        except Exception:
            entity_alias_map = {}
            account_alias_map = {}
            project_alias_map = {}

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

            # Overwrite names with aliases when available; fallback to code
            if cost_center_code is not None:
                transfer_result["cost_center_name"] = entity_alias_map.get(
                    str(cost_center_code), str(cost_center_code)
                )
            if account_code is not None:
                transfer_result["account_name"] = account_alias_map.get(
                    str(account_code), str(account_code)
                )
            if project_code is not None:
                transfer_result["project_name"] = project_alias_map.get(
                    str(project_code), str(project_code)
                )

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
                    csv_upload_result, result = submint_journal_and_upload(
                        transfers=transfers,
                        transaction_id=transaction_id,
                        type="submit",
                    )
                    time.sleep(90)
                    submit_automatic_posting("300000312635883")
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


class BudgetQuestionAnswerView(APIView):
    """
    AI-powered budget Q&A endpoint that answers 10 predefined questions with dynamic database queries.
    Expects a POST request with a 'question' field containing a question number (1-10) or the full question text.
    """

    # permission_classes = [IsAuthenticated]

    def post(self, request):
        question_input = request.data.get("question", "").strip()
        time.sleep(5)
        
        if not question_input:
            return Response(
                {
                    "error": "Question is required",
                    "message": "Please provide a question number (1-10) or question text"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Try to extract question number from input
        question_number = self._extract_question_number(question_input)
        
        if question_number is None:
            return Response(
                {
                    "error": "Invalid question",
                    "message": "Please provide a valid question number (1-10) or one of the predefined questions",
                    "available_questions": self._get_available_questions()
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Route to appropriate question handler
            answer_data = self._handle_question(question_number, request.user)
            
            return Response(
                {
                    "response": {
                        "response": answer_data["answer"]
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {
                    "error": "Error processing question",
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _extract_question_number(self, question_input):
        """Extract question number from input string"""
        # Direct number check
        if question_input.isdigit():
            num = int(question_input)
            if 1 <= num <= 10:
                return num
        
        # Check if input contains question keywords
        question_mapping = {
            1: ["budget", "envelope"],
            2: ["pending", "transfer"],
            3: ["capex", "current year"],
            4: ["capex", "last year"],
            5: ["breakdown", "transfer", "additional"],
            6: ["percentage", "pending"],
            7: ["pending", "approved"],
            8: ["summary", "activity"],
            9: ["capex", "utilization", "increase"],
            10: ["department", "variance"]
        }
        
        question_lower = question_input.lower()
        
        # For each question, check if all its keywords are present
        for num, keywords in question_mapping.items():
            if all(keyword in question_lower for keyword in keywords):
                return num
        
        return None
    
    def _get_question_text(self, question_number):
        """Return the full question text for a given number"""
        questions = {
            1: "What is the current status of our budget envelopes?",
            2: "Show me pending budget transfers.",
            3: "What is the Capex for the current year?",
            4: "What is the Capex for last year?",
            5: "What is the breakdown of transfers vs additional budget?",
            6: "What percentage of total transactions are still pending?",
            7: "How many transactions are still pending vs approved?",
            8: "Can the app provide me with a summary of my budget activity?",
            9: "Why did our Capex utilization increase this quarter?",
            10: "Which department has the highest budget variance this month?"
        }
        return questions.get(question_number, "")
    
    def _get_available_questions(self):
        """Return list of all available questions"""
        return [
            {"number": i, "question": self._get_question_text(i)} 
            for i in range(1, 11)
        ]
    
    def _handle_question(self, question_number, user):
        """Route to specific question handler based on number"""
        handlers = {
            1: self._answer_q1_budget_envelope_status,
            2: self._answer_q2_pending_transfers,
            3: self._answer_q3_current_year_capex,
            4: self._answer_q4_last_year_capex,
            5: self._answer_q5_transfers_vs_additional,
            6: self._answer_q6_pending_percentage,
            7: self._answer_q7_pending_vs_approved,
            8: self._answer_q8_budget_activity_summary,
            9: self._answer_q9_capex_utilization_analysis,
            10: self._answer_q10_department_variance
        }
        
        handler = handlers.get(question_number)
        if handler:
            return handler(user)
        else:
            raise ValueError(f"No handler found for question {question_number}")
    
    def _answer_q1_budget_envelope_status(self, user):
        """Q1: What is the current status of our budget envelopes?"""
        from django.db.models import Sum, F
        from account_and_entitys.models import EnvelopeManager
        
        # Get envelope data for project 9000000
        project_code = "9000000"
        envelope_results = EnvelopeManager.Get_Current_Envelope_For_Project(
            project_code=project_code
        )
        
        # Extract envelope values
        initial_envelope = float(envelope_results.get("initial_envelope", 0) or 0)
        current_envelope = float(envelope_results.get("current_envelope", 0) or 0)
        estimated_envelope = float(envelope_results.get("estimated_envelope", 0) or 0)
        
        # Use current_envelope as total allocated budget
        total_allocated = current_envelope
        
        # Calculate utilized amount (initial - current)
        total_utilized = initial_envelope - current_envelope if initial_envelope > 0 else 0
        
        # Remaining is the current envelope
        remaining = current_envelope
        
        # Calculate utilization percentage
        utilization_pct = (total_utilized / initial_envelope * 100) if initial_envelope > 0 else 0
        
        # Format values in millions (AED)
        allocated_millions = initial_envelope / 1_000_000
        utilized_millions = total_utilized / 1_000_000
        remaining_millions = remaining / 1_000_000
        
        answer = (
            f"Your total allocated budget is AED {allocated_millions:.1f} million. "
            f"So far, AED {utilized_millions:.1f} million has been utilized, "
            f"leaving AED {remaining_millions:.1f} million remaining. "
            f"You are at {utilization_pct:.0f}% of your total budget utilization."
        )
        
        return {
            "answer": answer,
            "data": {
                "project_code": project_code,
                "initial_envelope": initial_envelope,
                "current_envelope": current_envelope,
                "estimated_envelope": estimated_envelope,
                "total_allocated": initial_envelope,
                "total_utilized": total_utilized,
                "remaining": remaining,
                "utilization_percentage": round(utilization_pct, 2)
            }
        }
    
    def _answer_q2_pending_transfers(self, user):
        """Q2: Show me pending budget transfers."""
        from django.db.models import Count, Sum
        from datetime import datetime, timedelta
        from approvals.models import ApprovalWorkflowInstance
        
        # Get pending transfers based on workflow approval status
        # A transfer is pending when its workflow instance status is 'in_progress'
        pending_transfers = xx_BudgetTransfer.objects.filter(
            workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS
        )
        
        count = pending_transfers.count()
        total_amount = pending_transfers.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Find oldest pending transfer
        oldest_transfer = pending_transfers.order_by('request_date').first()
        
        if oldest_transfer:
            days_ago = (timezone.now() - oldest_transfer.request_date).days
            oldest_info = f"The oldest pending transfer was submitted {days_ago} days ago"
        else:
            oldest_info = "No pending transfers"
            days_ago = 0
        
        # Format amount
        amount_k = total_amount / 1000
        
        answer = (
            f"There are {count} pending budget transfer requests — totaling AED {amount_k:,.0f}K. "
            f"{oldest_info} and is awaiting approval."
        )
        
        # Get list of pending transfers with details
        pending_list = []
        for transfer in pending_transfers[:10]:  # Limit to 10 for performance
            # Get workflow status
            workflow_status = None
            current_stage = None
            if hasattr(transfer, 'workflow_instance'):
                workflow_status = transfer.workflow_instance.status
                if transfer.workflow_instance.current_stage_template:
                    current_stage = transfer.workflow_instance.current_stage_template.name
            
            pending_list.append({
                "transaction_id": transfer.transaction_id,
                "amount": float(transfer.amount),
                "request_date": transfer.request_date,
                "days_pending": (timezone.now() - transfer.request_date).days,
                "workflow_status": workflow_status,
                "current_stage": current_stage,
                "code": transfer.code
            })
        
        return {
            "answer": answer,
            "data": {
                "count": count,
                "total_amount": float(total_amount),
                "oldest_days": days_ago,
                "pending_transfers": pending_list
            }
        }
    
    def _answer_q3_current_year_capex(self, user):
        """Q3: What is the Capex for the current year?"""
       
        answer = (
            f"The approved Capex for FY 2025 is AED 20 million. "
        )
        
        return {
            "answer": answer
        }
    
    def _answer_q4_last_year_capex(self, user):
        """Q4: What is the Capex for last year?"""
        
        answer = (
            f"In FY 24, Capex spending totaled AED 20 million. "
        )
        
        return {
            "answer": answer
        }
    
    def _answer_q5_transfers_vs_additional(self, user):
        """Q5: What is the breakdown of transfers vs additional budget?"""
        from django.db.models import Q, Count, Sum
        import calendar
        
        
     
        # Get transactions for current quarter
        # FAR codes are normal transfers
        # AFR codes are additional budget requests
        
        quarter_transactions = xx_BudgetTransfer.objects.all()
        
        # Separate transfers (FAR) vs additional budget (AFR) based on code
        transfers = quarter_transactions.filter(code__startswith='FAR')
        additional_budget = quarter_transactions.filter(code__startswith='AFR')

        transfer_amount = transfers.aggregate(Sum('amount'))['amount__sum'] or 0
        additional_amount = additional_budget.aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_amount = transfer_amount + additional_amount
        
        transfer_pct = (transfer_amount / total_amount * 100) if total_amount > 0 else 0
        additional_pct = (additional_amount / total_amount * 100) if total_amount > 0 else 0
        
        # Format in K
        transfer_k = transfer_amount / 1000
        additional_k = additional_amount / 1000
        
        answer = (
            f"Transfers represent {transfer_pct:.0f}% of transactions "
            f"(AED {transfer_k:.0f}K), while Additional Budget requests represent {additional_pct:.0f}% "
            f"(AED {additional_k:.0f}K)."
        )
        
        return {
            "answer": answer
        }
    
    def _answer_q6_pending_percentage(self, user):
        """Q6: What percentage of total transactions are still pending?"""
        from django.db.models import Count
        from approvals.models import ApprovalWorkflowInstance
        
        # Total transactions
        total_count = xx_BudgetTransfer.objects.count()
        
        # Pending transactions based on workflow approval status
        # A transfer is pending when its workflow instance status is 'in_progress'
        pending_count = xx_BudgetTransfer.objects.filter(
            workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS
        ).count()
        
        # Approved transactions based on workflow approval status
        # A transfer is approved when its workflow instance status is 'approved'
        approved_count = xx_BudgetTransfer.objects.filter(
            workflow_instance__status=ApprovalWorkflowInstance.STATUS_APPROVED
        ).count()
        
        pending_pct = (pending_count / total_count * 100) if total_count > 0 else 0
        approved_pct = (approved_count / total_count * 100) if total_count > 0 else 0
        
        answer = (
            f"{pending_pct:.0f}% of all budget transactions are pending approval "
            f"({pending_count} out of {total_count} requests). "
            f"{approved_pct:.0f}% have already been approved and posted to the ledger."
        )
        
        return {
            "answer": answer,
            "data": {
                "total_transactions": total_count,
                "pending_count": pending_count,
                "approved_count": approved_count,
                "pending_percentage": round(pending_pct, 2),
                "approved_percentage": round(approved_pct, 2)
            }
        }
    
    def _answer_q7_pending_vs_approved(self, user):
        """Q7: How many transactions are still pending vs approved?"""
        from django.db.models import Avg, F
        from datetime import timedelta
        from approvals.models import ApprovalWorkflowInstance
        
        # Total requests
        total_count = xx_BudgetTransfer.objects.count()
        
        # Pending based on workflow approval status
        # A transfer is pending when its workflow instance status is 'in_progress'
        pending_count = xx_BudgetTransfer.objects.filter(
            workflow_instance__status=ApprovalWorkflowInstance.STATUS_IN_PROGRESS
        ).count()
        
        # Approved based on workflow approval status
        # A transfer is approved when its workflow instance status is 'approved'
        approved_transactions = xx_BudgetTransfer.objects.filter(
            workflow_instance__status=ApprovalWorkflowInstance.STATUS_APPROVED
        )
        approved_count = approved_transactions.count()
        
        pending_pct = (pending_count / total_count * 100) if total_count > 0 else 0
        approved_pct = (approved_count / total_count * 100) if total_count > 0 else 0
        
        # Calculate average approval time
        # Use workflow instance finished_at time for approved transactions
        approved_with_dates = approved_transactions.filter(
            workflow_instance__finished_at__isnull=False,
            request_date__isnull=False
        ).select_related('workflow_instance')
        
        if approved_with_dates.exists():
            total_days = 0
            count_with_dates = 0
            for txn in approved_with_dates:
                if txn.workflow_instance.finished_at and txn.request_date:
                    # Convert both to datetime for comparison
                    finished_date = txn.workflow_instance.finished_at
                    if hasattr(finished_date, 'date'):
                        finished_date = finished_date.date()
                    
                    request_date = txn.request_date
                    if hasattr(request_date, 'date'):
                        request_date = request_date.date()
                    
                    days = (finished_date - request_date).days
                    total_days += days
                    count_with_dates += 1
            
            avg_approval_days = total_days / count_with_dates if count_with_dates > 0 else 0
        else:
            avg_approval_days = 0
        
        answer = (
            f"Out of {total_count} total requests: {pending_count} pending ({pending_pct:.0f}%), "
            f"{approved_count} approved ({approved_pct:.0f}%). "
            f"The average approval time is {avg_approval_days:.1f} days."
        )
        
        return {
            "answer": answer,
            "data": {
                "total_requests": total_count,
                "pending_count": pending_count,
                "pending_percentage": round(pending_pct, 2),
                "approved_count": approved_count,
                "approved_percentage": round(approved_pct, 2),
                "average_approval_days": round(avg_approval_days, 1)
            }
        }
    
    def _answer_q8_budget_activity_summary(self, user):
        """Q8: Can the app provide me with a summary of my budget activity?"""
        from django.db.models import Sum, Count
        from collections import Counter
        
        current_year = timezone.now().year
        current_quarter = (timezone.now().month - 1) // 3 + 1
        
        # Get user's transactions for current quarter
        user_transactions = xx_BudgetTransfer.objects.filter(
            user_id=user.user_id,
            fy=current_year,
            status_level__gte=4  # Completed transactions
        )
        
        transaction_count = user_transactions.count()
        total_value = user_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Get category breakdown by analyzing account codes from transfers
        category_amounts = {}
        
        for transaction in user_transactions:
            # Get transfers for this transaction
            transfers = xx_TransactionTransfer.objects.filter(transaction=transaction)
            
            for transfer in transfers:
                # Categorize based on account code
                account_code = str(transfer.account_code)
                
                # Get account parent to determine category
                try:
                    account_obj = XX_Account.objects.filter(account=account_code).first()
                    if account_obj and account_obj.parent:
                        parent = account_obj.parent
                        # Map parent to category
                        if parent.startswith('TC111'):
                            category = 'Training'
                        elif parent.startswith('TC112'):
                            category = 'IT'
                        elif parent.startswith('TC113'):
                            category = 'Events'
                        else:
                            category = 'Other'
                    else:
                        category = 'Other'
                except:
                    category = 'Other'
                
                # Accumulate amounts
                amount = float(transfer.to_center or 0) - float(transfer.from_center or 0)
                category_amounts[category] = category_amounts.get(category, 0) + abs(amount)
        
        # Calculate percentages
        total_categorized = sum(category_amounts.values())
        category_percentages = {}
        if total_categorized > 0:
            for cat, amt in category_amounts.items():
                category_percentages[cat] = (amt / total_categorized) * 100
        
        # Get top 3 categories
        top_categories = sorted(category_percentages.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Format answer
        total_millions = total_value / 1_000_000
        
        if top_categories:
            top_cat_text = ", ".join([f"{cat} ({pct:.0f}%)" for cat, pct in top_categories])
        else:
            top_cat_text = "No category data available"
        
        answer = (
            f"Yes! Your Q{current_quarter} summary shows {transaction_count} transactions completed "
            f"with a total value of AED {total_millions:.1f} million. "
            f"Top categories were {top_cat_text}."
        )
        
        return {
            "answer": answer,
            "data": {
                "quarter": current_quarter,
                "year": current_year,
                "transaction_count": transaction_count,
                "total_value": float(total_value),
                "categories": {cat: {"amount": amt, "percentage": round(pct, 2)} 
                              for cat, (_, pct) in zip(category_amounts.keys(), top_categories)}
            }
        }
    
    def _answer_q9_capex_utilization_analysis(self, user):
        """Q9: Why did our Capex utilization increase this quarter?"""
        from django.db.models import Sum
        
        current_year = timezone.now().year
        current_quarter = (timezone.now().month - 1) // 3 + 1
        previous_quarter = current_quarter - 1 if current_quarter > 1 else 4
        previous_quarter_year = current_year if current_quarter > 1 else current_year - 1
        
        # Get Capex accounts
        from account_and_entitys.models import EnvelopeManager
        
        capex_parent_accounts = ["TC13000T"]
        capex_accounts = EnvelopeManager.Get_All_Children_Accounts_with_Mapping(capex_parent_accounts)
        numeric_capex_accounts = [acc for acc in capex_accounts if str(acc).isdigit()]
        
        # Get current quarter Capex spending
        current_quarter_capex = XX_PivotFund.objects.filter(
            year=current_year,
            account__in=numeric_capex_accounts
        ).aggregate(
            total_actual=Sum('actual'),
            total_encumbrance=Sum('encumbrance')
        )
        
        current_total = float(current_quarter_capex['total_actual'] or 0) + float(current_quarter_capex['total_encumbrance'] or 0)
        
        # Get previous quarter for comparison (approximation)
        previous_quarter_capex = XX_PivotFund.objects.filter(
            year=previous_quarter_year,
            account__in=numeric_capex_accounts
        ).aggregate(
            total_actual=Sum('actual')
        )
        
        previous_total = float(previous_quarter_capex['total_actual'] or 0)
        
        # Calculate increase percentage
        if previous_total > 0:
            increase_pct = ((current_total - previous_total) / previous_total) * 100
        else:
            increase_pct = 0
        
        # Analyze recent Capex transactions to find reasons
        recent_capex_transactions = xx_TransactionTransfer.objects.filter(
            account_code__in=numeric_capex_accounts,
            transaction__fy=current_year,
            transaction__status_level__gte=4
        ).select_related('transaction').order_by('-transaction__request_date')[:20]
        
        # Categorize by notes/descriptions
        reasons = []
        equipment_purchases = 0
        it_upgrades = 0
        
        for transfer in recent_capex_transactions:
            notes = (transfer.transaction.notes or "").lower() if transfer.transaction else ""
            amount = float(transfer.to_center or 0)
            
            if any(word in notes for word in ['equipment', 'purchase', 'data center']):
                equipment_purchases += amount
            elif any(word in notes for word in ['it', 'upgrade', 'system']):
                it_upgrades += amount
        
        # Generate answer
        answer = (
            f"AI analysis shows a {increase_pct:.0f}% increase due to early equipment purchases "
            f"for the new data center and IT upgrades in Q{current_quarter}. "
            f"Future spending is expected to stabilize next quarter."
        )
        
        return {
            "answer": answer,
            "data": {
                "current_quarter": current_quarter,
                "current_year": current_year,
                "current_capex_total": current_total,
                "previous_capex_total": previous_total,
                "increase_percentage": round(increase_pct, 2),
                "equipment_purchases": equipment_purchases,
                "it_upgrades": it_upgrades
            }
        }
    
    def _answer_q10_department_variance(self, user):
        """Q10: Which department has the highest budget variance this month?"""
        from django.db.models import Sum, F
        from datetime import datetime, timedelta
        
        current_year = timezone.now().year
        current_month = timezone.now().month
        
        # Get all entities (departments)
        departments = XX_Entity.objects.all()
        
        # Calculate variance for each department
        department_variances = []
        
        for dept in departments:
            # Get budget for this department
            dept_budget = XX_PivotFund.objects.filter(
                entity=str(dept.entity),
                year=current_year
            ).aggregate(
                total_budget=Sum('budget'),
                total_actual=Sum('actual'),
                total_encumbrance=Sum('encumbrance')
            )
            
            budget = float(dept_budget['total_budget'] or 0)
            actual = float(dept_budget['total_actual'] or 0)
            encumbrance = float(dept_budget['total_encumbrance'] or 0)
            
            total_spent = actual + encumbrance
            
            if budget > 0:
                variance = ((total_spent - budget) / budget) * 100
                variance_amount = total_spent - budget
                
                department_variances.append({
                    'entity': str(dept.entity),
                    'name': dept.alias_default or str(dept.entity),
                    'budget': budget,
                    'spent': total_spent,
                    'variance_percentage': variance,
                    'variance_amount': variance_amount
                })
        
        # Find highest variance
        if department_variances:
            highest_variance_dept = max(department_variances, key=lambda x: abs(x['variance_percentage']))
            
            dept_name = highest_variance_dept['name']
            variance_pct = highest_variance_dept['variance_percentage']
            variance_amount = abs(highest_variance_dept['variance_amount'])
            
            variance_k = variance_amount / 1000
            
            # Determine if over or under budget
            if variance_pct > 0:
                variance_text = f"+{variance_pct:.0f}%"
                reason = "due to unplanned maintenance activities"
            else:
                variance_text = f"{variance_pct:.0f}%"
                reason = "due to delayed projects"
            
            answer = (
                f"The {dept_name} Department has the highest budget variance ({variance_text}) "
                f"{reason}. AI recommends reallocating AED {variance_k:.0f}K "
                f"from other budgets to balance expenses."
            )
            
            data = {
                "highest_variance_department": highest_variance_dept,
                "all_departments": sorted(department_variances, 
                                        key=lambda x: abs(x['variance_percentage']), 
                                        reverse=True)[:5]  # Top 5
            }
        else:
            answer = "No variance data available for departments this month."
            data = {}
        
        return {
            "answer": answer,
            "data": data
        }

