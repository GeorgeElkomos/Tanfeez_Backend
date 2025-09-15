# upload_budget_fbdi.py
import argparse
import base64
from datetime import datetime
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("FUSION_BASE_URL").rstrip("/")
USER = os.getenv("FUSION_USER")
PASS = os.getenv("FUSION_PASS")

# Budget-specific environment variables (you may need to add these to your .env file)
DATA_ACCESS_SET_ID = os.getenv("FUSION_BUDGET_DAS_ID") or os.getenv("FUSION_DAS_ID")
LEDGER_ID = os.getenv("FUSION_LEDGER_ID")
SOURCE_NAME = os.getenv("FUSION_BUDGET_SOURCE_NAME", "BudgetTransfer")

def b64_csv(csv_path: str) -> str:
    """Read CSV file and encode in base64"""
    with open(csv_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def build_budget_soap_envelope(csv_b64_content: str, csv_filename: str, group_id: str, 
                               callback_url: str = None, notification_code: str = "10"):
    """Build the SOAP envelope for budget import using JournalImportLauncher (same as journal import)"""
    
    # Use same parameters as journal import: DataAccessSetId, SourceName, LedgerId, GroupId, PostErrorsToSuspense, CreateSummary, ImportDFF
    parameter_list = f"{DATA_ACCESS_SET_ID},{SOURCE_NAME},{LEDGER_ID},NULL,N,N,N"
    
    # Optional callback URL
    callback_section = f"<typ:callbackURL>{callback_url}</typ:callbackURL>" if callback_url else ""
    
    soap_envelope = f"""<?xml version="1.0" encoding="UTF-8"?>

<soapenv:Envelope xmlns:erp="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/" 
                  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
                  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
   <soapenv:Header/>
   <soapenv:Body>
      <typ:importBulkDataAsync>
         <typ:document>
            <erp:Content>{csv_b64_content}</erp:Content>
            <erp:FileName>{csv_filename}</erp:FileName>
            <erp:ContentType>csv</erp:ContentType>
         </typ:document>
         <typ:jobDetails>
           <erp:JobName>/oracle/apps/ess/financials/generalLedger/programs/common,JournalImportLauncher</erp:JobName>
            <erp:ParameterList>{parameter_list}</erp:ParameterList>
         </typ:jobDetails>
         <typ:notificationCode>{notification_code}</typ:notificationCode>
         {callback_section}
      </typ:importBulkDataAsync>
   </soapenv:Body>
</soapenv:Envelope>"""
    
    return soap_envelope


def upload_budget_fbdi_to_oracle(csv_file_path: str, group_id: str = None) -> dict:
    """
    Upload Budget FBDI CSV file to Oracle Fusion using SOAP API
    
    Args:
        csv_file_path: Path to the CSV file to upload
        group_id: Optional group ID for the upload (auto-generated if not provided)
    
    Returns:
        Dictionary with upload results
    """
    # Load environment variables
    load_dotenv()
    
    BASE_URL = os.getenv("FUSION_BASE_URL")
    USER = os.getenv("FUSION_USER") 
    PASS = os.getenv("FUSION_PASS")
    DATA_ACCESS_SET_ID = os.getenv("FUSION_BUDGET_DAS_ID") or os.getenv("FUSION_DAS_ID")
    LEDGER_ID = os.getenv("FUSION_LEDGER_ID")
    SOURCE_NAME = os.getenv("FUSION_BUDGET_SOURCE_NAME", "BudgetTransfer")
    
    # Sanity checks
    for k, v in {
        "FUSION_BASE_URL": BASE_URL,
        "FUSION_USER": USER,
        "FUSION_PASS": PASS,
        "FUSION_DAS_ID (or FUSION_BUDGET_DAS_ID)": DATA_ACCESS_SET_ID,
        "FUSION_LEDGER_ID": LEDGER_ID,
    }.items():
        if not v:
            return {"success": False, "error": f"Missing environment variable: {k}"}
    
    # Check if CSV file exists
    if not os.path.exists(csv_file_path):
        return {"success": False, "error": f"CSV file not found: {csv_file_path}"}
    
    # Auto-generate group ID if not provided
    if not group_id:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        group_id = f"BUDGET_{timestamp}"
    
    try:
        # Read and encode CSV
        csv_b64 = b64_csv(csv_file_path)
        csv_filename = os.path.basename(csv_file_path)
        
        # Build SOAP envelope for budget import
        soap_body = build_budget_soap_envelope(csv_b64, csv_filename, group_id)
        
        # SOAP headers
        headers = {
            "Content-Type": "text/xml; charset=utf-8", 
            "SOAPAction": "",
            "Accept": "text/xml"
        }
        
        # Determine SOAP endpoint
        if BASE_URL:
            soap_url = BASE_URL.replace("/fscmRestApi/resources/11.13.18.05", "/fscmService/ErpIntegrationService")
        else:
            return {"success": False, "error": "FUSION_BASE_URL not configured"}
        
        # Send SOAP request
        print(f"Uploading budget FBDI file: {csv_filename}")
        print(f"Group ID: {group_id}")
        print(f"SOAP URL: {soap_url}")
        
        response = requests.post(
            soap_url,
            auth=HTTPBasicAuth(USER, PASS),
            headers=headers,
            data=soap_body,
            timeout=120  # Slightly longer timeout for budget imports
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body (first 1000 chars): {response.text[:1000]}")
        
        if response.status_code >= 400:
            return {
                "success": False, 
                "error": f"HTTP Error: {response.status_code} {response.reason}",
                "response": response.text[:500]  # Truncate for logging
            }
        
        # Extract request ID from SOAP response
        import re
        result_match = re.search(r'<result[^>]*>(\d+)</result>', response.text)
        request_id = result_match.group(1) if result_match else None
        
        # Also look for fault or error messages
        fault_match = re.search(r'<faultstring[^>]*>(.*?)</faultstring>', response.text, re.DOTALL)
        if fault_match:
            fault_message = fault_match.group(1).strip()
            return {
                "success": False,
                "error": f"SOAP Fault: {fault_message}",
                "response": response.text[:1000]
            }
        
        # Additional debug: print if request_id is None
        if request_id is None:
            print("⚠️  WARNING: No request ID found in Oracle response")
            print(f"Full response: {response.text[:2000]}")
        
        return {
            "success": True,
            "request_id": request_id,
            "group_id": group_id,
            "csv_file": csv_filename,
            "message": "Budget FBDI file uploaded successfully to Oracle Fusion using JournalImportLauncher",
            "job_name": "JournalImportLauncher"
        }
        
    except Exception as e:
        return {"success": False, "error": f"Budget upload failed: {str(e)}"}


def upload_budget_from_zip(zip_file_path: str, group_id: str = None) -> dict:
    """
    Extract CSV from ZIP file and upload budget FBDI to Oracle Fusion
    
    Args:
        zip_file_path: Path to the ZIP file containing CSV
        group_id: Optional group ID for the upload
    
    Returns:
        Dictionary with upload results
    """
    import zipfile
    import tempfile
    
    if not os.path.exists(zip_file_path):
        return {"success": False, "error": f"ZIP file not found: {zip_file_path}"}
    
    try:
        # Extract CSV from ZIP to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # Find CSV file in ZIP
                csv_files = [f for f in zip_ref.namelist() if f.lower().endswith('.csv')]
                
                if not csv_files:
                    return {"success": False, "error": "No CSV file found in ZIP"}
                
                # Extract the first CSV file found
                csv_filename = csv_files[0]
                zip_ref.extract(csv_filename, temp_dir)
                csv_path = os.path.join(temp_dir, csv_filename)
                
                # Upload the extracted CSV
                return upload_budget_fbdi_to_oracle(csv_path, group_id)
                
    except Exception as e:
        return {"success": False, "error": f"Failed to process ZIP file: {str(e)}"}


if __name__ == "__main__":
    """
    Example usage for testing budget FBDI upload
    """
    parser = argparse.ArgumentParser(description="Upload Budget FBDI to Oracle Fusion")
    parser.add_argument("file_path", help="Path to CSV or ZIP file to upload")
    parser.add_argument("--group-id", help="Optional group ID for the upload")
    
    args = parser.parse_args()
    
    if args.file_path.lower().endswith('.zip'):
        result = upload_budget_from_zip(args.file_path, args.group_id)
    elif args.file_path.lower().endswith('.csv'):
        result = upload_budget_fbdi_to_oracle(args.file_path, args.group_id)
    else:
        print("Error: File must be either CSV or ZIP format")
        exit(1)
    
    if result["success"]:
        print(f"✅ Upload successful!")
        print(f"Request ID: {result.get('request_id', 'N/A')}")
        print(f"Group ID: {result.get('group_id', 'N/A')}")
        print(f"Message: {result.get('message', 'N/A')}")
    else:
        print(f"❌ Upload failed: {result['error']}")
        exit(1)