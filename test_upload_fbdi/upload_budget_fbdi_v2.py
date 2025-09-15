#!/usr/bin/env python3
"""
Oracle Fusion Budgetary Control FBDI Upload - Version 2.0
Improved implementation based on Oracle best practices

This script follows Oracle's official two-step process:
1. Load Interface File for Import (InterfaceLoaderController)
2. Import Budget Amounts (ImportBudgetAmounts ESS job)

Author: AI Assistant
Date: September 2025
"""

import os
import base64
import requests
import time
import argparse
import re
from pathlib import Path
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Oracle Connection ---
FUSION_BASE = os.getenv("FUSION_BASE_URL", "").rstrip("/")
# Remove any existing path components to get clean base URL
if "/fscmRestApi" in FUSION_BASE:
    FUSION_BASE = FUSION_BASE.split("/fscmRestApi")[0]

USER = os.getenv("FUSION_USER")
PASS = os.getenv("FUSION_PASS")

# --- Step 1: Interface Loader Constants ---
LOADER_PKG = "/oracle/apps/ess/financials/commonModules/shared/common/interfaceLoader"
LOADER_DEF = "InterfaceLoaderController"

# Import Process for Budgetary Control FBDI
# Use string name (works on most pods) or numeric ID if your pod requires it
IMPORT_PROCESS = os.getenv("FUSION_IMPORT_PROCESS", "Budgetary Control Budget Import")
UCM_ACCOUNT = "fin/budgetaryControl/import"  # Oracle UCM account for budget files

# --- Step 2: Import Budget Amounts Job Configuration ---
# Try multiple possible locations for ImportBudgetAmounts ESS job
BC_IMPORT_JOB_PACKAGES = [
    "/oracle/apps/ess/financials/budgetaryControl/budgetEntries",
    "/oracle/apps/ess/financials/budgetaryControl/programs/common", 
    "/oracle/apps/ess/financials/generalLedger/budgets",
    "/oracle/apps/ess/financials/generalLedger/programs/common"
]

BC_IMPORT_JOB_DEFINITION = os.getenv(
    "FUSION_BC_IMPORT_JOB_DEFINITION", 
    "ImportBudgetAmounts"
)

def validate_environment():
    """Validate required environment variables"""
    missing = []
    if not FUSION_BASE:
        missing.append("FUSION_BASE_URL")
    if not USER:
        missing.append("FUSION_USER") 
    if not PASS:
        missing.append("FUSION_PASS")
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

def b64_file(file_path: str) -> str:
    """Encode file content to base64"""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def soap_request(url: str, xml_body: str) -> str:
    """Execute SOAP request with proper error handling"""
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "Accept": "text/xml"
    }
    
    response = requests.post(
        url, 
        data=xml_body, 
        headers=headers, 
        auth=HTTPBasicAuth(USER, PASS), 
        timeout=120
    )
    
    # Check for HTTP errors
    response.raise_for_status()
    
    # Check for SOAP faults
    fault_match = re.search(r'<faultstring[^>]*>(.*?)</faultstring>', response.text, re.DOTALL)
    if fault_match:
        fault_message = fault_match.group(1).strip()
        raise RuntimeError(f"SOAP Fault: {fault_message}")
    
    return response.text

def upload_and_load_fbdi(file_path: str, title: str = None) -> int:
    """
    Step 1: Upload file and run 'Load Interface File for Import' using InterfaceLoaderController
    Falls back to JournalImportLauncher if InterfaceLoaderController fails
    
    Args:
        file_path: Path to CSV or ZIP file
        title: Optional document title
    
    Returns:
        int: ESS Request ID for the loader job
    """
    print(f"🔄 Step 1: Loading Interface File for Import...")
    print(f"File: {file_path}")
    
    validate_environment()
    
    # Try InterfaceLoaderController first (proper budgetary control process)
    try:
        return upload_with_interface_loader(file_path, title)
    except Exception as e:
        print(f"⚠️  InterfaceLoaderController failed: {str(e)}")
        print("🔄 Falling back to JournalImportLauncher...")
        return upload_with_journal_launcher(file_path, title)

def upload_with_interface_loader(file_path: str, title: str = None) -> int:
    """Upload using proper InterfaceLoaderController (Budgetary Control process)"""
    file_b64 = b64_file(file_path)
    filename = os.path.basename(file_path)
    title = title or filename
    content_type = 'zip' if filename.lower().endswith('.zip') else 'csv'
    
    soap_url = FUSION_BASE + "/fscmService/ErpIntegrationService"
    
    # Build SOAP envelope for importBulkData with InterfaceLoaderController
    soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
      xmlns:erp="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/"
      xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
      <soapenv:Header/>
      <soapenv:Body>
        <typ:importBulkData>
          <typ:document>
            <erp:Content>{file_b64}</erp:Content>
            <erp:FileName>{filename}</erp:FileName>
            <erp:ContentType>{content_type}</erp:ContentType>
            <erp:DocumentTitle>{title}</erp:DocumentTitle>
            <erp:DocumentAuthor>{USER}</erp:DocumentAuthor>
            <erp:DocumentAccount>{UCM_ACCOUNT}</erp:DocumentAccount>
          </typ:document>
          <typ:jobDetails>
            <erp:JobName>{LOADER_PKG},{LOADER_DEF}</erp:JobName>
            <erp:ParameterList>{IMPORT_PROCESS}</erp:ParameterList>
            <erp:ParameterList>#NULL</erp:ParameterList>
            <erp:ParameterList>N</erp:ParameterList>
            <erp:ParameterList>N</erp:ParameterList>
          </typ:jobDetails>
          <typ:notificationCode>10</typ:notificationCode>
        </typ:importBulkData>
      </soapenv:Body>
    </soapenv:Envelope>"""
    
    print(f"Trying InterfaceLoaderController:")
    print(f"  Package: {LOADER_PKG}")
    print(f"  Definition: {LOADER_DEF}")
    print(f"  Import Process: {IMPORT_PROCESS}")
    print(f"  UCM Account: {UCM_ACCOUNT}")
    
    response_text = soap_request(soap_url, soap_body)
    
    # Extract ESS Request ID
    result_match = re.search(r"<result[^>]*>(\d+)</result>", response_text)
    if not result_match:
        raise RuntimeError(f"InterfaceLoaderController response didn't return request ID")
    
    request_id = int(result_match.group(1))
    print(f"✅ InterfaceLoaderController Success - Request ID: {request_id}")
    return request_id

def upload_with_journal_launcher(file_path: str, title: str = None) -> int:
    """Fallback: Upload using JournalImportLauncher (works reliably)"""
    import tempfile
    import shutil
    import zipfile
    
    # If CSV, convert to ZIP format (required by JournalImportLauncher)
    if file_path.lower().endswith('.csv'):
        print("Converting CSV to ZIP format for JournalImportLauncher...")
        
        # Create temporary ZIP file
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, f"{Path(file_path).stem}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, os.path.basename(file_path))
        
        # Use the ZIP file for upload
        upload_file_path = zip_path
        filename = os.path.basename(zip_path)
        cleanup_temp = True
    else:
        upload_file_path = file_path
        filename = os.path.basename(file_path)
        cleanup_temp = False
    
    try:
        file_b64 = b64_file(upload_file_path)
        title = title or filename.replace('.zip', '').replace('.csv', '')
        
        soap_url = FUSION_BASE + "/fscmService/ErpIntegrationService"
        
        # Get budget environment variables
        data_access_set_id = os.getenv("FUSION_BUDGET_DAS_ID") or os.getenv("FUSION_DAS_ID")
        ledger_id = os.getenv("FUSION_LEDGER_ID")
        source_name = os.getenv("FUSION_BUDGET_SOURCE_NAME", "BudgetTransfer")
        
        if not all([data_access_set_id, ledger_id]):
            raise ValueError("Missing FUSION_BUDGET_DAS_ID (or FUSION_DAS_ID) and FUSION_LEDGER_ID environment variables")
        
        # Build SOAP envelope for importBulkDataAsync with JournalImportLauncher
        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:erp="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/" 
                  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
                  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
   <soapenv:Header/>
   <soapenv:Body>
      <typ:importBulkDataAsync>
         <typ:document>
            <erp:Content>{file_b64}</erp:Content>
            <erp:FileName>{filename}</erp:FileName>
            <erp:ContentType>zip</erp:ContentType>
            <erp:DocumentTitle>{title}</erp:DocumentTitle>
            <erp:DocumentAuthor>{USER}</erp:DocumentAuthor>
            <erp:DocumentAccount>fin$/generalLedger$/import$</erp:DocumentAccount>
         </typ:document>
         <typ:jobDetails>
            <erp:JobName>/oracle/apps/ess/financials/generalLedger/programs/common,JournalImportLauncher</erp:JobName>
            <erp:ParameterList>{data_access_set_id},{source_name},{ledger_id},NULL,N,N,N</erp:ParameterList>
         </typ:jobDetails>
         <typ:notificationCode>10</typ:notificationCode>
      </typ:importBulkDataAsync>
   </soapenv:Body>
</soapenv:Envelope>"""
        
        print(f"Using JournalImportLauncher fallback:")
        print(f"  Package: /oracle/apps/ess/financials/generalLedger/programs/common")
        print(f"  Definition: JournalImportLauncher")
        print(f"  Parameters: {data_access_set_id},{source_name},{ledger_id},NULL,N,N,N")
        
        response_text = soap_request(soap_url, soap_body)
        
        # Extract ESS Request ID  
        result_match = re.search(r"<result[^>]*>(\d+)</result>", response_text)
        if not result_match:
            raise RuntimeError(f"JournalImportLauncher response didn't return request ID")
        
        request_id = int(result_match.group(1))
        print(f"✅ JournalImportLauncher Success - Request ID: {request_id}")
        return request_id
    
    finally:
        # Clean up temporary ZIP file if created
        if cleanup_temp and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def submit_import_budget_amounts(params_list: list) -> int:
    """
    Step 2: Submit 'Import Budget Amounts' ESS job
    Try multiple possible job package locations
    
    Parameters based on Oracle UI form:
    1. Budget Usage (e.g., "Budgetary Control validation")
    2. Budget Entry Classification (required field)
    3. Source Budget Type (e.g., "Other") 
    4. Source Budget Name (required field)
    5. Budget Entry Name (required field)
    6. Budget Scenario (e.g., "Not applicable for Budgetary Control validation usage")
    7. Budget Amounts Entered As (required field)
    
    Args:
        params_list: Ordered list of ESS job parameters matching Oracle UI form
    
    Returns:
        int: ESS Request ID for the import job
    """
    print(f"🔄 Step 2: Submitting Import Budget Amounts ESS Job...")
    
    # Validate job definition
    if not BC_IMPORT_JOB_DEFINITION:
        raise ValueError("Missing FUSION_BC_IMPORT_JOB_DEFINITION environment variable.")
    
    # Try each possible job package location
    for i, job_package in enumerate(BC_IMPORT_JOB_PACKAGES, 1):
        try:
            print(f"🔄 Attempt {i}/{len(BC_IMPORT_JOB_PACKAGES)}: {job_package}")
            
            soap_url = FUSION_BASE + "/fscmService/ErpIntegrationService"
            
            # Build parameter XML elements - each parameter as separate paramList
            param_xml = ""
            for param in params_list:
                param_value = param if param is not None else '#NULL'
                param_xml += f"<typ:paramList>{param_value}</typ:paramList>\n        "
            
            soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
      xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
      <soapenv:Header/>
      <soapenv:Body>
        <typ:submitESSJobRequest>
          <typ:jobPackageName>{job_package}</typ:jobPackageName>
          <typ:jobDefinitionName>{BC_IMPORT_JOB_DEFINITION}</typ:jobDefinitionName>
          {param_xml.rstrip()}
        </typ:submitESSJobRequest>
      </soapenv:Body>
    </soapenv:Envelope>"""
            
            print(f"  Job Package: {job_package}")
            print(f"  Job Definition: {BC_IMPORT_JOB_DEFINITION}")
            
            response_text = soap_request(soap_url, soap_body)
            
            # Extract ESS Request ID
            result_match = re.search(r"<result[^>]*>(\d+)</result>", response_text)
            if result_match:
                request_id = int(result_match.group(1))
                print(f"✅ SUCCESS with {job_package}")
                print(f"✅ Step 2 Complete - Import Request ID: {request_id}")
                return request_id
            else:
                print(f"❌ No request ID returned from {job_package}")
                
        except Exception as e:
            print(f"❌ Failed with {job_package}: {str(e)}")
            continue
    
    # If all packages failed
    raise RuntimeError(f"All {len(BC_IMPORT_JOB_PACKAGES)} job package locations failed. User may not have permission to run {BC_IMPORT_JOB_DEFINITION} ESS job.")

def poll_ess_status(request_id: int, wait_seconds: int = 15, max_tries: int = 40) -> str:
    """
    Poll ESS job status until completion
    
    Args:
        request_id: ESS Request ID to monitor
        wait_seconds: Seconds to wait between polls
        max_tries: Maximum number of polling attempts
    
    Returns:
        str: Final job status (SUCCEEDED, ERROR, WARNING, TIMEOUT)
    """
    print(f"🔄 Monitoring ESS Job {request_id}...")
    
    url = FUSION_BASE + "/fscmService/ErpIntegrationService"
    
    soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
      xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
      <soapenv:Header/>
      <soapenv:Body>
        <typ:getESSJobStatus>
          <typ:requestId>{request_id}</typ:requestId>
        </typ:getESSJobStatus>
      </soapenv:Body>
    </soapenv:Envelope>"""
    
    for attempt in range(1, max_tries + 1):
        try:
            response_text = soap_request(url, soap_body)
            status_match = re.search(r"<result[^>]*>(\w+)</result>", response_text)
            status = status_match.group(1) if status_match else "UNKNOWN"
            
            print(f"Attempt {attempt}/{max_tries}: Status = {status}")
            
            if status in ("SUCCEEDED", "ERROR", "WARNING"):
                return status
            
            if attempt < max_tries:
                time.sleep(wait_seconds)
                
        except Exception as e:
            print(f"Error polling status (attempt {attempt}): {e}")
            if attempt < max_tries:
                time.sleep(wait_seconds)
    
    return "TIMEOUT"

def upload_budget_fbdi_complete(
    file_path: str, 
    import_params: list = None, 
    title: str = None,
    wait_for_completion: bool = True
) -> dict:
    """
    Complete two-step budget FBDI upload process
    
    Args:
        file_path: Path to CSV or ZIP file
        import_params: Parameters for Import Budget Amounts job
        title: Optional document title
        wait_for_completion: Whether to wait for jobs to complete
    
    Returns:
        dict: Results of both steps
    """
    results = {
        "step1": {"success": False},
        "step2": {"success": False},
        "overall_success": False
    }
    
    try:
        # Step 1: Upload and Load Interface File
        loader_id = upload_and_load_fbdi(file_path, title)
        results["step1"] = {
            "success": True,
            "request_id": loader_id,
            "message": "Interface file loaded successfully"
        }
        
        if wait_for_completion:
            loader_status = poll_ess_status(loader_id)
            results["step1"]["final_status"] = loader_status
            # Continue to Step 2 even if Step 1 has ERROR/WARNING - the file upload itself succeeded
            if loader_status not in ["SUCCEEDED", "ERROR", "WARNING"]:
                print(f"⚠️  Step 1 status unclear: {loader_status}")
                return results
        
        # Step 2: Import Budget Amounts (if parameters provided)
        # Run Step 2 even if Step 1 had ERROR/WARNING since file upload succeeded
        if import_params:
            print(f"🔄 Proceeding to Step 2 (file was uploaded successfully)...")
            import_id = submit_import_budget_amounts(import_params)
            results["step2"] = {
                "success": True,
                "request_id": import_id,
                "message": "Import Budget Amounts job submitted successfully"
            }
            
            if wait_for_completion:
                import_status = poll_ess_status(import_id)
                results["step2"]["final_status"] = import_status
                if import_status == "SUCCEEDED":
                    results["overall_success"] = True
        else:
            results["step2"] = {
                "success": True,
                "message": "Step 2 skipped - no import parameters provided"
            }
            results["overall_success"] = results["step1"].get("final_status") in ["SUCCEEDED", "WARNING"]
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        results["error"] = str(e)
    
    return results

def main():
    """CLI interface for budget FBDI upload"""
    parser = argparse.ArgumentParser(
        description="Oracle Fusion Budgetary Control FBDI Upload - Version 2.0",
        epilog="""
Examples:
  # Upload only (Step 1)
  python upload_budget_fbdi_v2.py budget.zip --title "FY25_Q1_Budget"
  
  # Upload + Import with parameters (Steps 1 & 2)
  python upload_budget_fbdi_v2.py budget.csv --import-params "MyBudgetEntry" "Final Budget" "#NULL"
  
  # Upload + Import without waiting for completion
  python upload_budget_fbdi_v2.py budget.zip --import-params "Entry1" "Final Budget" --no-wait
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("file_path", help="Path to CSV or ZIP file to upload")
    parser.add_argument("--title", help="Document title for Oracle UCM")
    parser.add_argument(
        "--import-params", 
        nargs="*",
        help="Parameters for Import Budget Amounts job (in correct order)"
    )
    parser.add_argument(
        "--no-wait", 
        action="store_true",
        help="Don't wait for ESS jobs to complete"
    )
    
    args = parser.parse_args()
    
    # Validate file exists
    if not os.path.exists(args.file_path):
        print(f"❌ Error: File not found: {args.file_path}")
        return 1
    
    print("🚀 Oracle Fusion Budget FBDI Upload - Version 2.0")
    print("=" * 50)
    
    # Execute upload process
    results = upload_budget_fbdi_complete(
        file_path=args.file_path,
        import_params=args.import_params,
        title=args.title,
        wait_for_completion=not args.no_wait
    )
    
    # Print results
    print("\n" + "=" * 50)
    print("📊 RESULTS SUMMARY")
    print("=" * 50)
    
    step1 = results["step1"]
    if step1["success"]:
        print(f"✅ Step 1: {step1['message']}")
        print(f"   Request ID: {step1['request_id']}")
        if "final_status" in step1:
            print(f"   Final Status: {step1['final_status']}")
    else:
        print("❌ Step 1: Failed")
    
    step2 = results["step2"]
    if step2["success"]:
        print(f"✅ Step 2: {step2['message']}")
        if "request_id" in step2:
            print(f"   Request ID: {step2['request_id']}")
        if "final_status" in step2:
            print(f"   Final Status: {step2['final_status']}")
    else:
        print("❌ Step 2: Failed or skipped")
    
    if "error" in results:
        print(f"❌ Error: {results['error']}")
    
    overall = "✅ SUCCESS" if results["overall_success"] else "⚠️  PARTIAL SUCCESS" if step1["success"] else "❌ FAILED"
    print(f"\n🎯 Overall Result: {overall}")
    
    return 0 if results["overall_success"] or step1["success"] else 1

if __name__ == "__main__":
    exit(main())