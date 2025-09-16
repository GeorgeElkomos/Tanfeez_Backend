# upload_budget_fbdi.py
import argparse
import base64
from datetime import datetime
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from urllib.parse import urlsplit

load_dotenv()

BASE_URL = os.getenv("FUSION_BASE_URL").rstrip("/") if os.getenv("FUSION_BASE_URL") else None
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


def _soap_endpoint_from_base(url: str | None) -> str | None:
    """Build the correct SOAP endpoint from a base URL that may include REST paths."""
    if not url:
        return None
    parts = urlsplit(url)
    if parts.scheme and parts.netloc:
        root = f"{parts.scheme}://{parts.netloc}"
    else:
        root = url.split('/')[0]
        if not root.startswith('http'):
            root = f"https://{root}"
    return root.rstrip('/') + '/fscmService/ErpIntegrationService'


def upload_gl_budget_interface_zip(zip_file_path: str,
                                   document_account: str = 'fin/generalLedgerBudgetBalance/import',
                                   security_group: str = None,
                                   import_process_code: str | None = None,
                                   job_name: str = '/oracle/apps/ess/financials/commonModules/shared/common/interfaceLoader;InterfaceLoaderController',
                                   async_call: bool = True) -> dict:
    """Upload a GL Budget Interface ZIP via importBulkData(/Async) and return ESS request id.

    This mirrors the GL interface flow: upload ZIP to UCM + run InterfaceLoader with ParamList where the service injects DocumentId.
    - document_account defaults to GL budget interface account
    - import_process_code is required (GL_IMPORT_PROCESS_CODE env if not provided)
    """
    load_dotenv()
    base_url = os.getenv('FUSION_BASE_URL')
    user = os.getenv('FUSION_USER')
    pwd = os.getenv('FUSION_PASS')
    if not all([base_url, user, pwd]):
        return {"success": False, "error": "Missing FUSION_BASE_URL/FUSION_USER/FUSION_PASS"}

    if not os.path.exists(zip_file_path):
        return {"success": False, "error": f"ZIP not found: {zip_file_path}"}

    endpoint = _soap_endpoint_from_base(base_url)
    if not endpoint:
        return {"success": False, "error": "Invalid SOAP endpoint derived from BASE_URL"}

    # Determine params
    sg = security_group or os.getenv('SECURITY_GROUP', 'FAFusionImportExport')
    proc_code = import_process_code or os.getenv('GL_IMPORT_PROCESS_CODE')
    if not proc_code:
        return {"success": False, "error": "GL_IMPORT_PROCESS_CODE not set"}
    param_list = f"{proc_code},#NULL,N,N"

    # Build envelope
    with open(zip_file_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')

    op = 'importBulkDataAsync' if async_call else 'importBulkData'
    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/"
  xmlns:erp="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/">
  <soapenv:Header/>
  <soapenv:Body>
    <typ:{op}>
      <typ:document>
        <erp:Content>{b64}</erp:Content>
        <erp:FileName>{os.path.basename(zip_file_path)}</erp:FileName>
        <erp:ContentType>zip</erp:ContentType>
        <erp:DocumentTitle>{os.path.splitext(os.path.basename(zip_file_path))[0]}</erp:DocumentTitle>
        <erp:DocumentName>{os.path.splitext(os.path.basename(zip_file_path))[0]}</erp:DocumentName>
        <erp:DocumentSecurityGroup>{sg}</erp:DocumentSecurityGroup>
        <erp:DocumentAccount>{document_account}</erp:DocumentAccount>
      </typ:document>
      <typ:jobDetails>
        <erp:JobName>{job_name}</erp:JobName>
        <erp:ParameterList>{param_list}</erp:ParameterList>
      </typ:jobDetails>
      <typ:notificationCode>#NULL</typ:notificationCode>
      <typ:callbackURL>#NULL</typ:callbackURL>
      <typ:jobOptions>#NULL</typ:jobOptions>
    </typ:{op}>
  </soapenv:Body>
</soapenv:Envelope>"""

    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': '',
        'Accept': 'text/xml'
    }
    try:
        print(f"Uploading GL Budget Interface ZIP via {op}...")
        print(f"Endpoint: {endpoint}")
        r = requests.post(endpoint, data=envelope, headers=headers, auth=HTTPBasicAuth(user, pwd), timeout=180)
        print(f"Response Status: {r.status_code}")
        if r.status_code >= 400:
            return {"success": False, "error": f"HTTP {r.status_code} {r.reason}", "response": r.text[:1000]}

        # Extract ESS request id
        import re
        m = re.search(r'<result>(\d+)</result>', r.text)
        req_id = m.group(1) if m else None
        fault = re.search(r'<faultstring>(.*?)</faultstring>', r.text, re.DOTALL)
        if fault:
            return {"success": False, "error": f"SOAP Fault: {fault.group(1).strip()}", "response": r.text[:2000]}

        return {"success": True, "request_id": req_id, "message": "GL Budget Interface submitted"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def submit_import_budget_amounts(data_access_set_id: str, ledger_id: str, source_name: str = "BudgetTransfer") -> dict:
    """
    Submit 'Import Budget Amounts' ESS job via SOAP after file upload
    This is Step 2: Run the separate ESS job to import the budget amounts
    
    Args:
        data_access_set_id: Data Access Set ID
        ledger_id: Ledger ID
        source_name: Source Name for the budget import
    
    Returns:
        Dictionary with import job results
    """
    load_dotenv()
    
    BASE_URL = os.getenv("FUSION_BASE_URL")
    USER = os.getenv("FUSION_USER") 
    PASS = os.getenv("FUSION_PASS")
    
    if not all([BASE_URL, USER, PASS]):
        return {"success": False, "error": "Missing Oracle connection environment variables"}
    
    # Try multiple possible ESS job locations for ImportBudgetAmounts
    job_locations = [
        {
            "package": "/oracle/apps/ess/financials/generalLedger/programs/common",
            "job": "ImportBudgetAmounts",
            "description": "Standard GL Common Package"
        },
        {
            "package": "/oracle/apps/ess/financials/generalLedger/budgets",
            "job": "ImportBudgetAmounts", 
            "description": "GL Budgets Package"
        },
        {
            "package": "/oracle/apps/ess/financials/generalLedger/programs",
            "job": "ImportBudgetAmounts",
            "description": "GL Programs Package"
        }
    ]
    
    for job_info in job_locations:
        try:
            # Build SOAP envelope for ESS Job Submission
            parameter_list = f"{data_access_set_id}##{source_name}##{ledger_id}"
            
            soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
                  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
   <soapenv:Header/>
   <soapenv:Body>
      <typ:submitESSJobRequest>
         <typ:jobPackageName>{job_info['package']}</typ:jobPackageName>
         <typ:jobDefinitionName>{job_info['job']}</typ:jobDefinitionName>
         <typ:parameterList>{parameter_list}</typ:parameterList>
      </typ:submitESSJobRequest>
   </soapenv:Body>
</soapenv:Envelope>"""
            
            # ESS Job Submission endpoint
            ess_url = BASE_URL.replace("/fscmRestApi/resources/11.13.18.05", "/fscmService/ErpIntegrationService")
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/submitESSJobRequest",
                "Accept": "text/xml"
            }
            
            print(f"🔄 Trying ESS Job: {job_info['description']}")
            print(f"Job Package: {job_info['package']}")
            print(f"Job Name: {job_info['job']}")
            print(f"Parameters: {parameter_list}")
            
            response = requests.post(
                ess_url,
                auth=HTTPBasicAuth(USER, PASS),
                headers=headers,
                data=soap_body,
                timeout=120
            )
            
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                # Success! Extract job request ID
                import re
                result_match = re.search(r'<result[^>]*>(\d+)</result>', response.text)
                request_id = result_match.group(1) if result_match else None
                
                # Check for SOAP faults
                fault_match = re.search(r'<faultstring[^>]*>(.*?)</faultstring>', response.text, re.DOTALL)
                if not fault_match:
                    print(f"✅ SUCCESS with {job_info['description']}")
                    return {
                        "success": True,
                        "request_id": request_id,
                        "message": f"Import Budget Amounts ESS Job submitted successfully using {job_info['description']}",
                        "job_name": job_info['job'],
                        "job_package": job_info['package']
                    }
                else:
                    fault_message = fault_match.group(1).strip()
                    print(f"❌ SOAP Fault: {fault_message[:200]}")
            else:
                print(f"❌ HTTP {response.status_code}: {response.reason}")
                
        except Exception as e:
            print(f"❌ Error trying {job_info['description']}: {str(e)}")
            continue
    
    return {
        "success": False,
        "error": "All ESS job location attempts failed. User may not have permission to run ImportBudgetAmounts ESS job.",
        "recommendation": "Contact Oracle administrator to grant access to ImportBudgetAmounts ESS job definition."
    }


def upload_budget_fbdi_to_oracle(csv_file_path: str, group_id: str = None, run_import_process: bool = True) -> dict:
    """
    Upload Budget FBDI CSV file to Oracle Fusion using SOAP API
    
    Args:
        csv_file_path: Path to the CSV file to upload
        group_id: Optional group ID for the upload (auto-generated if not provided)
        run_import_process: Whether to run 'Import Budget Amounts' after file upload
    
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
        
        result = {
            "success": True,
            "request_id": request_id,
            "group_id": group_id,
            "csv_file": csv_filename,
            "message": "Budget FBDI file uploaded successfully to Oracle Fusion using JournalImportLauncher",
            "job_name": "JournalImportLauncher"
        }
        
        # Step 2: Run Import Budget Amounts process if requested
        if run_import_process:
            print(f"\n🔄 Running Step 2: Import Budget Amounts process...")
            import_result = submit_import_budget_amounts(DATA_ACCESS_SET_ID, LEDGER_ID, SOURCE_NAME)
            result["import_budget_amounts"] = import_result
            
            if import_result["success"]:
                print(f"✅ Import Budget Amounts submitted successfully")
                print(f"Import Request ID: {import_result.get('request_id', 'N/A')}")
                result["message"] += " and Import Budget Amounts process submitted"
            else:
                print(f"⚠️ Import Budget Amounts failed: {import_result['error']}")
                # Don't fail the whole process, just add warning
                result["message"] += " but Import Budget Amounts failed"
        
        return result
        
    except Exception as e:
        return {"success": False, "error": f"Budget upload failed: {str(e)}"}


def upload_budget_from_zip(zip_file_path: str, group_id: str = None, run_import_process: bool = True) -> dict:
    """
    Extract CSV from ZIP file and upload budget FBDI to Oracle Fusion
    
    Args:
        zip_file_path: Path to the ZIP file containing CSV
        group_id: Optional group ID for the upload
        run_import_process: Whether to run 'Import Budget Amounts' after upload
    
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
                
                # Upload the extracted CSV with import process option
                return upload_budget_fbdi_to_oracle(csv_path, group_id, run_import_process)
                
    except Exception as e:
        return {"success": False, "error": f"Failed to process ZIP file: {str(e)}"}


if __name__ == "__main__":
    """
    Example usage for testing budget FBDI upload with complete process
    """
    parser = argparse.ArgumentParser(description="Upload Budget FBDI/ZIP to Oracle Fusion")
    parser.add_argument("file_path", help="Path to CSV or ZIP file to upload")
    parser.add_argument("--group-id", help="Optional group ID for the upload")
    parser.add_argument("--no-import", action="store_true", 
                       help="Skip running 'Import Budget Amounts' process after upload")
    parser.add_argument("--use-gl-interface", action="store_true", help="For ZIP: use GL Budget Interface flow instead of CSV JournalImport")
    
    args = parser.parse_args()
    
    # Determine whether to run import process (default: True, unless --no-import flag)
    run_import = not args.no_import
    
    if args.file_path.lower().endswith('.zip'):
        if args.use_gl_interface:
            result = upload_gl_budget_interface_zip(args.file_path)
        else:
            result = upload_budget_from_zip(args.file_path, args.group_id, run_import)
    elif args.file_path.lower().endswith('.csv'):
        result = upload_budget_fbdi_to_oracle(args.file_path, args.group_id, run_import)
    else:
        print("Error: File must be either CSV or ZIP format")
        exit(1)
    
    if result["success"]:
        print(f"✅ Upload successful!")
        print(f"Request ID: {result.get('request_id', 'N/A')}")
        print(f"Group ID: {result.get('group_id', 'N/A')}")
        print(f"Message: {result.get('message', 'N/A')}")
        
        # Show import process results if available
        if "import_budget_amounts" in result:
            import_result = result["import_budget_amounts"]
            if import_result["success"]:
                print(f"📊 Import Budget Amounts Request ID: {import_result.get('request_id', 'N/A')}")
            else:
                print(f"⚠️ Import Budget Amounts Error: {import_result['error']}")
    else:
        print(f"❌ Upload failed: {result['error']}")
        exit(1)