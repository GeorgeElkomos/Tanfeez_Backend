#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Oracle Fusion Expense Item Creation
Simple function to create expense items with all configuration in one place
"""

import requests
import json
from datetime import date


def create_expense_item(
    # Oracle Fusion Configuration
    base_url="https://hcbg-dev4.fa.ocs.oraclecloud.com",
    username="BCARSE",
    password="123456789",
    
    # Expense Details
    receipt_date=None,
    expense_template="MIC HQ Regular Expenses",
    expense_type="Airfare",
    amount=1200.00,
    currency="AED",
    description="Business trip to Dubai – airfare ticket",
    
    # Project Details
    project_number="HQIACE001",
    task_number="1.01",
    expenditure_org="MIC Headquarter BU",
    
    # Additional Details
    reimbursable=True,
    assignment_id=300000123456789,
    agency_name="Lightidea Travel Agency",
    audit_reason="Travel for client meeting",
    
    # DFF Context (Flexfield)
    flex_context="Expense_Project_Context"
):
    """
    Create an expense item in Oracle Fusion
    
    Args:
        base_url: Oracle Fusion base URL
        username: Oracle username
        password: Oracle password
        receipt_date: Date of receipt (defaults to today)
        expense_template: Expense template name
        expense_type: Type of expense (Airfare, Hotel, etc.)
        amount: Billed amount
        currency: Currency code (AED, USD, etc.)
        description: Expense description
        project_number: Project number
        task_number: Task number
        expenditure_org: Expenditure organization name
        reimbursable: Whether expense is reimbursable
        assignment_id: Employee assignment ID
        agency_name: Agency name
        audit_reason: Reason for audit adjustment
        flex_context: DFF context name
        
    Returns:
        dict: Response from Oracle Fusion (success or error details)
    """
    
    # Default receipt date to today if not provided
    if receipt_date is None:
        receipt_date = str(date.today())
    
    # === COMPLETE PAYLOAD ===
    payload = {
        "ReceiptDate": receipt_date,
        "ExpenseTemplate": expense_template,
        "ExpenseTypeCategoryCode": expense_type,
        "BilledAmount": amount,
        "BilledCurrencyCode": currency,
        "Description": description,
        "ProjectNumber": project_number,
        "TaskNumber": task_number,
        "ExpenditureOrganizationName": expenditure_org,
        "ReimbursableFlag": reimbursable,
        "AssignmentId": assignment_id,
        "AgencyName": agency_name,
        "AuditAdjustmentReason": audit_reason,
        "expenseItemDff": [
            {
                "__FLEX_Context": flex_context,
                "Attribute1": project_number,
                "Attribute2": task_number,
                "Attribute3": expenditure_org
            }
        ]
    }
    
    # === REQUEST CONFIGURATION ===
    endpoint = f"{base_url}/fscmRestApi/resources/latest/expenses"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "REST-Framework-Version": "2",
        "Oracle-Mobile-Backend-Id": "fscmRestApi",
        "User-Agent": "FusionExpenseClient/1.0"
    }
    
    # === SEND REQUEST ===
    print(f"🚀 Creating expense item in Oracle Fusion...")
    print(f"   Endpoint: {endpoint}")
    print(f"   Expense Type: {expense_type}")
    print(f"   Amount: {amount} {currency}")
    print(f"   Project: {project_number} / Task: {task_number}")
    
    try:
        response = requests.post(
            endpoint,
            auth=(username, password),
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        # === HANDLE RESPONSE ===
        if response.status_code in (200, 201):
            print("✅ Expense item created successfully!")
            result = {
                "status": "success",
                "status_code": response.status_code,
                "data": response.json(),
                "headers": dict(response.headers)
            }
            print(json.dumps(result["data"], indent=2))
            return result
        else:
            print(f"❌ Error: {response.text}")
            result = {
                "status": "error",
                "status_code": response.status_code,
                "error": response.text,
                "headers": dict(response.headers)
            }
            return result
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Network or connection error"
        }


# === EXAMPLE USAGE ===
if __name__ == "__main__":
    print("=" * 60)
    print("Oracle Fusion - Create Expense Item")
    print("=" * 60)
    
    # Simple usage with defaults
    result = create_expense_item()
    
    print("\n" + "=" * 60)
    print("Result:")
    print(json.dumps(result, indent=2))
    print("=" * 60)
    
    # # Custom usage example:
    # result = create_expense_item(
    #     username="YOUR_USERNAME",
    #     password="YOUR_PASSWORD",
    #     expense_type="Hotel",
    #     amount=850.00,
    #     description="Hotel stay in Abu Dhabi",
    #     project_number="HQIACE002",
    #     task_number="2.01"
    # )
