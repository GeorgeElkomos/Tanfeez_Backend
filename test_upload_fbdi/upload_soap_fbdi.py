# upload_soap_fbdi.py
import argparse
import base64
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

def build_soap_envelope(csv_b64_content: str, csv_filename: str, group_id: str, 
                       callback_url: str = None, notification_code: str = "10"):
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

def main():
    parser = argparse.ArgumentParser(description="Upload CSV to Fusion using SOAP importBulkDataAsync")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--group-id", help="GL Interface GROUP_ID in your CSV rows (optional - auto-generated if not provided)")
    parser.add_argument("--callback-url", help="Optional callback URL for notifications")
    parser.add_argument("--notification-code", default="10", help="Notification code (default: 10)")
    args = parser.parse_args()

    # Auto-generate group ID if not provided
    if not args.group_id:
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        args.group_id = timestamp  # Pure numeric format: YYYYMMDDHHMISS
        print(f"Auto-generated Group ID: {args.group_id}")

    # Sanity checks
    for k, v in {
        "FUSION_BASE_URL": BASE_URL,
        "FUSION_USER": USER,
        "FUSION_PASS": PASS,
        "FUSION_DAS_ID": DATA_ACCESS_SET_ID,
        "FUSION_LEDGER_ID": LEDGER_ID,
    }.items():
        if not v:
            raise RuntimeError(f"Missing env var: {k}")

    if not os.path.exists(args.csv):
        raise FileNotFoundError(f"CSV file not found: {args.csv}")

    # Read and encode CSV
    csv_b64 = b64_csv(args.csv)
    csv_filename = os.path.basename(args.csv)
    
    print(f"Uploading CSV: {csv_filename} (size: {len(csv_b64)} base64 chars)")
    print(f"Parameters: DAS={DATA_ACCESS_SET_ID}, Source={SOURCE_NAME}, Ledger={LEDGER_ID}, Group={args.group_id}")

    # Build SOAP envelope
    soap_body = build_soap_envelope(
        csv_b64, csv_filename, args.group_id, 
        args.callback_url, args.notification_code
    )

    # SOAP headers
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "",
        "Accept": "text/xml"
    }

    # Determine SOAP endpoint - typically /fscmService/ErpIntegrationService
    # You may need to adjust this based on your Oracle Fusion setup
    soap_url = BASE_URL.replace("/fscmRestApi/resources/11.13.18.05", "/fscmService/ErpIntegrationService")
    
    print(f"SOAP URL: {soap_url}")
    print("Sending SOAP request...")

    # Send SOAP request
    response = requests.post(
        soap_url,
        auth=HTTPBasicAuth(USER, PASS),
        headers=headers,
        data=soap_body
    )

    print(f"Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")

    if response.status_code >= 400:
        print(f"HTTP Error: {response.status_code} {response.reason}")
        response.raise_for_status()
    else:
        print("SOAP request sent successfully!")
        
        # Extract request ID from SOAP response
        import re
        result_match = re.search(r'<result[^>]*>(\d+)</result>', response.text)
        if result_match:
            request_id = result_match.group(1)
            print(f"ESS Job Request ID: {request_id}")
            print("You can monitor this job in Oracle Fusion ESS (Scheduled Processes).")
        else:
            print("Could not extract request ID from response. Check the raw response above.")

if __name__ == "__main__":
    main()
