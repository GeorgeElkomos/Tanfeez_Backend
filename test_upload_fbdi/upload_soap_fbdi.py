# upload_soap_fbdi.py
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

DATA_ACCESS_SET_ID = os.getenv("FUSION_DAS_ID")
LEDGER_ID = os.getenv("FUSION_LEDGER_ID")
SOURCE_NAME = os.getenv("FUSION_SOURCE_NAME", "Manual")

def b64_csv(csv_path: str) -> str:
    """Read CSV file and encode in base64"""
    with open(csv_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def build_soap_envelope(csv_b64_content: str, csv_filename: str, group_id: str, callback_url: str = None, notification_code: str = "10") -> str:
    """Build the SOAP envelope for importBulkDataAsync"""
    
    # Build parameter list: DataAccessSetId, SourceName, LedgerId, GroupId, PostErrorsToSuspense, CreateSummary, ImportDFF
    parameter_list = f"{DATA_ACCESS_SET_ID},{SOURCE_NAME},{LEDGER_ID},{group_id},N,N,N"

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



def upload_fbdi_to_oracle(csv_file_path: str, group_id: str = None) -> dict:
    """
    Upload FBDI CSV file to Oracle Fusion using SOAP API
    
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
    DATA_ACCESS_SET_ID = os.getenv("FUSION_DAS_ID")
    LEDGER_ID = os.getenv("FUSION_LEDGER_ID")
    SOURCE_NAME = os.getenv("FUSION_SOURCE_NAME", "Manual")
    
    # Sanity checks
    for k, v in {
        "FUSION_BASE_URL": BASE_URL,
        "FUSION_USER": USER,
        "FUSION_PASS": PASS,
        "FUSION_DAS_ID": DATA_ACCESS_SET_ID,
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
        group_id = timestamp
    
    try:
        # Read and encode CSV
        csv_b64 = b64_csv(csv_file_path)
        csv_filename = os.path.basename(csv_file_path)
        
        # Build SOAP envelope
        soap_body = build_soap_envelope(csv_b64, csv_filename, group_id=group_id)
        
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
        response = requests.post(
            soap_url,
            auth=HTTPBasicAuth(USER, PASS),
            headers=headers,
            data=soap_body,
            timeout=60
        )
        
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
        
        return {
            "success": True,
            "request_id": request_id,
            "group_id": group_id,
            "csv_file": csv_filename,
            "message": "FBDI file uploaded successfully to Oracle Fusion"
        }
        
    except Exception as e:
        return {"success": False, "error": f"Upload failed: {str(e)}"}
