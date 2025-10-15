import requests
import json
from datetime import date
import base64

# === 1. Your Oracle Fusion environment info ===
FUSION_BASE_URL = "https://hcbg-dev4.fa.ocs.oraclecloud.com"
USERNAME = "BCARSE"
PASSWORD = "123456789"

# === 2. Endpoint for creating expense item ===
ENDPOINT = f"{FUSION_BASE_URL}/fscmRestApi/resources/latest/expenses"

# === 3. Encode a local PDF attachment (optional) ===
def encode_file(filepath):
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# Example: encoded receipt file (optional)
# encoded_receipt = encode_file("Airfare_Receipt.pdf")

# === 4. Expense JSON payload ===
payload = {
    "ReceiptDate": str(date.today()),  # e.g. 2025-10-16
    "ExpenseTemplate": "MIC HQ Regular Expenses",
    "ExpenseTypeCategoryCode": "Airfare",
    "BilledAmount": 1200.00,
    "BilledCurrencyCode": "AED",
    "Description": "Business trip to Dubai – airfare ticket",
    "AssignmentId": 300000123456789,  # retrieved from HCM
    "AgencyName": "Lightidea Travel Agency",
    "AuditAdjustmentReason": "Travel for client meeting",
    "expenseDff": [
        {
            "__FLEX_Context": "MIC_HQ",    # this context name may differ in your setup
            "Attribute1": "HQIACE001",   # Project Number
            "Attribute2": "1.01",        # Task Number
            "Attribute3": "Internal Audit"  # Expenditure Org or other field
        }
    ]
    # "Attachments": [
    #     {
    #         "FileName": "Airfare_Receipt.pdf",
    #         "ContentType": "application/pdf",
    #         "AttachmentCategory": "ExpenseReceipt",
    #         "FileContent": encoded_receipt
    #     }
    # ]
}

# === 5. Preferred headers per Oracle docs ===
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "REST-Framework-Version": "2",   # Oracle-recommended header
    "Oracle-Mobile-Backend-Id": "fscmRestApi",  # optional: identifies backend service
    "User-Agent": "FusionExpenseClient/1.0"
}

# === 6. POST request ===
response = requests.post(
    ENDPOINT,
    auth=(USERNAME, PASSWORD),
    headers=headers,
    data=json.dumps(payload)
)

# === 7. Check result ===
if response.status_code in (200, 201):
    print("✅ Expense item created successfully!")
    print(json.dumps(response.json(), indent=4))
else:
    print(f"❌ Error {response.status_code}: {response.text}")
