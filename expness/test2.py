import requests
import json
from datetime import date

BASE = "https://hcbg-dev4.fa.ocs.oraclecloud.com"
USERNAME = "BCARSE"
PASSWORD = "123456789"

COMMON_HEADERS = {
    "Content-Type": "application/vnd.oracle.adf.resourceitem+json",
    "Accept": "application/json",
    "REST-Framework-Version": "2"
}

def create_expense():
    payload = {
        "Description": "Airfare to Dubai (test via API)",
        "ReceiptDate": str(date.today()),
        "ExpenseTemplate": "MIC HQ Regular Expenses",
        "ExpenseType": "Airfare",
        "ReceiptAmount": 1200.00,
        "ReceiptCurrencyCode": "AED",
        "ReimbursableAmount": 1200.00,
        "ExpenseSource": "CASH",
        "AssignmentId": 300000123456789   # TODO: real HCM AssignmentId
    }
    url = f"{BASE}/fscmRestApi/resources/11.13.18.05/expenses"
    r = requests.post(url, auth=(USERNAME, PASSWORD),headers=COMMON_HEADERS, data=json.dumps(payload))
    if r.status_code not in (200, 201):
        raise RuntimeError(f"[Create Expense] {r.status_code} {r.text}")
    body = r.json()
    self_href = next(l["href"] for l in body.get("links", []) if l.get("rel") == "self")
    expense_id = body["ExpenseId"]
    org_id = body.get("OrgId")  # required on distribution
    print("✅ Expense created:", expense_id)
    return self_href, expense_id, org_id

def add_distribution(expense_self_href,
                     expense_id,
                     org_id,
                     project_number=None,
                     task_number=None,
                     expenditure_org_name=None,
                     reimbursable_amount=None):
    """
    POST: /expenses/{expensesUniqID}/child/ExpenseDistribution
    Add Project/Task + Expenditure Organization via PJCDFF on the distribution.
    PJCDFF segments (context EXM_Expense_Report_Line) include:
      _PROJECT_ID_Display, _TASK_ID_Display, _ORGANIZATION_ID_Display
    """
    url = f"{expense_self_href}/child/ExpenseDistribution"

    dist = {
        "ExpenseId": expense_id,
        "OrgId": org_id
    }
    if reimbursable_amount is not None:
        dist["ReimbursableAmount"] = reimbursable_amount

    pjcdff = {"__FLEX_Context": "EXM_Expense_Report_Line"}
    if project_number:
        pjcdff["_PROJECT_ID_Display"] = project_number
    if task_number:
        pjcdff["_TASK_ID_Display"] = task_number
    if expenditure_org_name:
        pjcdff["_ORGANIZATION_ID_Display"] = expenditure_org_name  # Expenditure Organization

    # Only add PJCDFF array if we actually set any segment
    if any(k in pjcdff for k in ("_PROJECT_ID_Display", "_TASK_ID_Display", "_ORGANIZATION_ID_Display")):
        dist["PJCDFF"] = [pjcdff]

    r = requests.post(url, auth=(USERNAME, PASSWORD),
                      headers=COMMON_HEADERS, data=json.dumps(dist))
    if r.status_code not in (200, 201):
        raise RuntimeError(f"[Add Distribution] {r.status_code} {r.text}")

    print("✅ Distribution added (Project/Task/Exp Org set where provided)")
    return r.json()

if __name__ == "__main__":
    PROJECT_NUMBER = "HQIACE001"
    TASK_NUMBER = "1.01"
    EXPENDITURE_ORG_NAME = "Internal Audit"  # Must match the Expenditure Organization name (HR org)

    try:
        expense_href, expense_id, org_id = create_expense()
        add_distribution(
            expense_self_href=expense_href,
            expense_id=expense_id,
            org_id=org_id,
            project_number=PROJECT_NUMBER,
            task_number=TASK_NUMBER,
            expenditure_org_name=EXPENDITURE_ORG_NAME,
            reimbursable_amount=1200.00
        )
    except Exception as e:
        print("❌ Error:", e)
