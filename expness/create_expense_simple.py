#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Oracle Fusion Expense Creation with Project Distribution
Single function with all configuration in one place
"""

import requests
import json
from datetime import date


def create_expense_with_distribution(
    # === Oracle Fusion Configuration ===
    base_url="https://hcbg-dev4.fa.ocs.oraclecloud.com",
    username="BCARSE",
    password="123456789",
    
    # === Expense Header Details ===
    description="Airfare to Dubai (test via API)",
    receipt_date=None,
    expense_template="MIC HQ Regular Expenses",
    expense_type="Airfare",
    receipt_amount=1200.00,
    receipt_currency="AED",
    reimbursable_amount=1200.00,
    expense_source="CASH",
    assignment_id=300000123456789,
    
    # === Project Distribution Details ===
    project_number="HQIACE001",
    task_number="1.01",
    expenditure_org_name="Internal Audit"
):
    """
    Create an expense with project distribution in Oracle Fusion.
    All configuration and payload in one function.
    
    Args:
        base_url: Oracle Fusion base URL
        username: Oracle username
        password: Oracle password
        description: Expense description
        receipt_date: Receipt date (defaults to today)
        expense_template: Expense template name
        expense_type: Type of expense (Airfare, Hotel, etc.)
        receipt_amount: Receipt amount
        receipt_currency: Currency code
        reimbursable_amount: Reimbursable amount
        expense_source: Expense source (CASH, CARD, etc.)
        assignment_id: Employee assignment ID
        project_number: Project number
        task_number: Task number
        expenditure_org_name: Expenditure organization name
        
    Returns:
        dict: Complete response with expense and distribution details
    """
    
    # Default receipt date to today
    if receipt_date is None:
        receipt_date = str(date.today())
    
    # === COMMON HEADERS ===
    headers = {
        "Content-Type": "application/vnd.oracle.adf.resourceitem+json",
        "Accept": "application/json",
        "REST-Framework-Version": "2"
    }
    
    print("=" * 70)
    print("🚀 Creating Expense in Oracle Fusion")
    print("=" * 70)
    
    # ============================================
    # STEP 1: CREATE EXPENSE HEADER
    # ============================================
    expense_payload = {
        "Description": description,
        "ReceiptDate": receipt_date,
        "ExpenseTemplate": expense_template,
        "ExpenseType": expense_type,
        "ReceiptAmount": receipt_amount,
        "ReceiptCurrencyCode": receipt_currency,
        "ReimbursableAmount": reimbursable_amount,
        "ExpenseSource": expense_source,
        "AssignmentId": assignment_id,

        
    }
    
    expense_url = f"{base_url}/fscmRestApi/resources/11.13.18.05/expenses"
    
    print(f"\n📝 Step 1: Creating Expense Header")
    print(f"   URL: {expense_url}")
    print(f"   Description: {description}")
    print(f"   Type: {expense_type}")
    print(f"   Amount: {receipt_amount} {receipt_currency}")
    
    try:
        expense_response = requests.post(
            expense_url,
            auth=(username, password),
            headers=headers,
            data=json.dumps(expense_payload),
            timeout=30
        )
        
        if expense_response.status_code not in (200, 201):
            error_msg = f"[Create Expense] {expense_response.status_code} {expense_response.text}"
            print(f"❌ Error: {error_msg}")
            return {
                "status": "error",
                "step": "create_expense",
                "status_code": expense_response.status_code,
                "error": expense_response.text
            }
        
        expense_body = expense_response.json()
        expense_self_href = next(l["href"] for l in expense_body.get("links", []) if l.get("rel") == "self")
        expense_id = expense_body["ExpenseId"]
        org_id = expense_body.get("OrgId")
        
        print(f"✅ Expense created successfully!")
        print(f"   ExpenseId: {expense_id}")
        print(f"   OrgId: {org_id}")
        
    except Exception as e:
        print(f"❌ Exception during expense creation: {str(e)}")
        return {
            "status": "error",
            "step": "create_expense",
            "error": str(e)
        }
    
    # ============================================
    # STEP 2: ADD DISTRIBUTION WITH PROJECT/TASK
    # ============================================
    distribution_url = f"{expense_self_href}/child/ExpenseDistribution"
    
    # Build distribution payload
    distribution_payload = {
        "ExpenseId": expense_id,
        "OrgId": org_id,
        "ReimbursableAmount": reimbursable_amount
    }
    
    # Build PJCDFF (Project Costing DFF)
    pjcdff = {
        "__FLEX_Context": "EXM_Expense_Report_Line",
        "_PROJECT_ID_Display": project_number,
        "_TASK_ID_Display": task_number,
        "_ORGANIZATION_ID_Display": expenditure_org_name
    }
    
    distribution_payload["PJCDFF"] = [pjcdff]
    
    print(f"\n📊 Step 2: Adding Distribution with Project/Task")
    print(f"   URL: {distribution_url}")
    print(f"   Project: {project_number}")
    print(f"   Task: {task_number}")
    print(f"   Expenditure Org: {expenditure_org_name}")
    
    try:
        distribution_response = requests.post(
            distribution_url,
            auth=(username, password),
            headers=headers,
            data=json.dumps(distribution_payload),
            timeout=30
        )
        
        if distribution_response.status_code not in (200, 201):
            error_msg = f"[Add Distribution] {distribution_response.status_code} {distribution_response.text}"
            print(f"❌ Error: {error_msg}")
            return {
                "status": "error",
                "step": "add_distribution",
                "status_code": distribution_response.status_code,
                "error": distribution_response.text,
                "expense_id": expense_id
            }
        
        distribution_body = distribution_response.json()
        
        print(f"✅ Distribution added successfully!")
        print(f"   Project/Task/Expenditure Org configured")
        
    except Exception as e:
        print(f"❌ Exception during distribution creation: {str(e)}")
        return {
            "status": "error",
            "step": "add_distribution",
            "error": str(e),
            "expense_id": expense_id
        }
    
    # ============================================
    # RETURN COMPLETE RESULT
    # ============================================
    result = {
        "status": "success",
        "expense": {
            "expense_id": expense_id,
            "org_id": org_id,
            "self_href": expense_self_href,
            "details": expense_body
        },
        "distribution": {
            "project_number": project_number,
            "task_number": task_number,
            "expenditure_org": expenditure_org_name,
            "details": distribution_body
        }
    }
    
    print("\n" + "=" * 70)
    print("✅ COMPLETE: Expense with Distribution Created Successfully!")
    print("=" * 70)
    
    return result


# === EXAMPLE USAGE ===
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Oracle Fusion - Create Expense with Project Distribution")
    print("=" * 70)
    
    # Call with defaults
    result = create_expense_with_distribution()
    
    # Display result
    print("\n📋 Final Result:")
    print(json.dumps(result, indent=2))
    
    # # Custom usage example:
    # result = create_expense_with_distribution(
    #     username="YOUR_USERNAME",
    #     password="YOUR_PASSWORD",
    #     description="Hotel in Abu Dhabi",
    #     expense_type="Hotel",
    #     receipt_amount=850.00,
    #     project_number="HQIACE002",
    #     task_number="2.01",
    #     expenditure_org_name="Finance Department"
    # )
