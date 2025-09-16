#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, re, base64, zipfile, requests, xml.etree.ElementTree as ET
from dotenv import load_dotenv

# ================= USER CONFIG =================
ZIP_PATH = r"test_upload_fbdi\XccBudgetInterface.zip"   # must contain XccBudgetInterface.csv at ROOT
CSV_REQUIRED_NAME = "XccBudgetInterface.csv"

# UCM metadata
DOCUMENT_SECURITY_GROUP = "FAFusionImportExport"
DOCUMENT_ACCOUNT = "fin/budgetaryControl/import"

# Polling settings
POLL_SECS = 10
# =================================================

def normalize_base(url: str) -> str:
    """Normalize the base URL by removing service-specific paths"""
    if not url: return ""
    url = url.strip().rstrip("/")
    for tok in ["/fscmRestApi/resources", "/fscmRestApi", "/fscmService", "/webservices", "/soa-infra"]:
        i = url.find(tok)
        if i != -1: url = url[:i]
    return url

def load_env():
    """Load environment variables for Oracle Fusion connection"""
    load_dotenv()
    base_url = normalize_base(
        os.getenv("FUSION_BASE_URL") or
        os.getenv("ORACLE_FUSION_URL") or
        "https://hcbg.fa.em2.oraclecloud.com"  # change if you intend dev4
    )
    user = os.getenv("FUSION_USER") or os.getenv("ORACLE_USERNAME") or "AFarghaly"
    pwd  = os.getenv("FUSION_PASS") or os.getenv("ORACLE_PASSWORD")
    if not pwd: pwd = input("Oracle Fusion password: ")
    return base_url, user, pwd

def validate_zip(zip_path: str):
    """Validate that ZIP file exists and contains required CSV at root"""
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"ZIP not found: {zip_path}")
    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        print("📦 ZIP contents:", names)
        if any(n.endswith("/") for n in names):
            raise ValueError("ZIP contains subfolders. Put files at ZIP ROOT (no folders).")
        if names.count(CSV_REQUIRED_NAME) != 1:
            raise ValueError(f"ZIP must contain exactly one '{CSV_REQUIRED_NAME}' at ROOT.")
        extras = [n for n in names if n != CSV_REQUIRED_NAME]
        if extras:
            print("⚠️  Extra files detected:", extras, " (recommended: only the CSV).")

def b64_file(path: str) -> str:
    """Encode file to base64 string"""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def post_soap(endpoint: str, user: str, pwd: str, xml: str, soap_action: str = "") -> requests.Response:
    """Post SOAP request to Oracle Fusion"""
    headers = {
        "Content-Type": "text/xml; charset=UTF-8",
        "Accept": "text/xml",
        "SOAPAction": soap_action
    }
    print(f"\n➡️  POST {endpoint}  (SOAPAction: {headers['SOAPAction']!r})")
    r = requests.post(endpoint, data=xml, headers=headers, auth=(user, pwd), timeout=180)
    
    # Handle 415 with SOAP 1.2 retry
    if r.status_code == 415:
        print(f'🔁 415 detected, retrying with SOAP 1.2...')
        headers_12 = headers.copy()
        headers_12['Content-Type'] = f'application/soap+xml; charset=utf-8; action="{soap_action}"'
        r2 = requests.post(endpoint, data=xml, headers=headers_12, auth=(user, pwd), timeout=180)
        print(f'SOAP 1.2 retry status: {r2.status_code}')
        if r2.status_code < 400:
            r = r2  # Use the successful retry response
    
    print("HTTP", r.status_code)
    print(r.text[:1400])
    return r

def extract_envelope(text: str) -> str | None:
    """Extract SOAP envelope from response, handling multipart/related format"""
    # Handle multipart/related responses (common in Oracle Fusion)
    if "multipart/related" in text and "----=" in text:
        # Find the XML content part after multipart boundary
        parts = text.split("----=")
        for part in parts:
            if "Content-Type: application/xop+xml" in part or "text/xml" in part:
                # Find the actual XML content after headers
                lines = part.split('\n')
                in_headers = True
                xml_lines = []
                for line in lines:
                    if in_headers:
                        if line.strip() == '':  # Empty line indicates end of headers
                            in_headers = False
                        continue
                    if line.startswith('----='):  # Start of next part
                        break
                    xml_lines.append(line)
                xml_content = '\n'.join(xml_lines).strip()
                if xml_content and '<' in xml_content:
                    # Extract just the envelope
                    m = re.search(r'(<(?:\w+:)?Envelope[\s\S]*?</(?:\w+:)?Envelope>)', xml_content)
                    if m:
                        return m.group(1)
                    return xml_content
    
    # Fallback to original logic for non-multipart responses
    m = re.search(r'(<(?:\w+:)?Envelope[\s\S]*?</(?:\w+:)?Envelope>)', text)
    return m.group(1) if m else None

def parse_fault_and_vals(resp_text: str):
    """Parse SOAP response for faults and extract values"""
    xml = extract_envelope(resp_text)
    if not xml: return "NO_SOAP_ENVELOPE_FOUND", {}
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        return f"PARSE_ERROR: {e}", {}

    ns11 = "{http://schemas.xmlsoap.org/soap/envelope/}"
    ns12 = "{http://www.w3.org/2003/05/soap-envelope}"
    fault = root.find(f".//{ns11}Fault") or root.find(f".//{ns12}Fault")
    if fault is not None:
        fc = fault.find("faultcode") or fault.find(f"{ns12}Code/{ns12}Value")
        fs = fault.find("faultstring") or fault.find(f"{ns12}Reason/{ns12}Text")
        return f"{fc.text if fc is not None else ''} | {fs.text if fs is not None else ''}", {}

    vals = {}
    for e in root.iter():
        t = e.tag.lower()
        if "documentid" in t and e.text:
            vals["DocumentId"] = e.text.strip()
        if "jobrequestid" in t and e.text and e.text.strip().isdigit():
            vals.setdefault("JobRequestIds", []).append(e.text.strip())
        if t.endswith("result") and e.text:
            v = e.text.strip()
            vals.setdefault("Results", []).append(v)

    # Promote numeric <result> → JobRequestIds if none present
    if "JobRequestIds" not in vals:
        numeric_results = [r for r in vals.get("Results", []) if r.isdigit()]
        if numeric_results:
            vals["JobRequestIds"] = numeric_results

    return None, vals

def upload_to_ucm(zip_path: str) -> str:
    """Upload ZIP file to UCM and return DocumentId"""
    base_url, user, pwd = load_env()
    endpoint = f"{base_url}/fscmService/ErpIntegrationService"
    validate_zip(zip_path)
    zip_b64 = b64_file(zip_path)
    
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:erp="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/"
                  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
  <soapenv:Header/>
  <soapenv:Body>
    <typ:uploadFileToUcm>
      <typ:document>
        <erp:Content>{zip_b64}</erp:Content>
        <erp:FileName>{os.path.basename(zip_path)}</erp:FileName>
        <erp:ContentType>zip</erp:ContentType>
        <erp:DocumentSecurityGroup>{DOCUMENT_SECURITY_GROUP}</erp:DocumentSecurityGroup>
        <erp:DocumentAccount>{DOCUMENT_ACCOUNT}</erp:DocumentAccount>
      </typ:document>
    </typ:uploadFileToUcm>
  </soapenv:Body>
</soapenv:Envelope>"""

    r = post_soap(endpoint, user, pwd, xml)
    if r.status_code != 200: 
        raise SystemExit(f"uploadFileToUcm HTTP {r.status_code}")
    
    fault, vals = parse_fault_and_vals(r.text)
    if fault: 
        raise SystemExit(f"uploadFileToUcm fault: {fault}")
    
    doc_id = vals.get("DocumentId") or (vals.get("Results") or [None])[0]
    if not doc_id: 
        raise SystemExit("No DocumentId returned.")
    
    print(f"✅ Uploaded to UCM. DocumentId={doc_id}")
    return doc_id

def submit_interface_loader(document_id: str) -> str:
    """Submit Interface Loader job with the document ID"""
    base_url, user, pwd = load_env()
    endpoint = f"{base_url}/fscmService/ErpIntegrationService"

    xml = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
<soapenv:Header/>
<soapenv:Body>
<typ:submitESSJobRequest>
<typ:jobPackageName>/oracle/apps/ess/financials/commonModules/shared/common/interfaceLoader/</typ:jobPackageName>
<typ:jobDefinitionName>InterfaceLoaderController</typ:jobDefinitionName>
<!--Zero or more repetitions:-->
<typ:paramList>51</typ:paramList>
<typ:paramList>{document_id}</typ:paramList>
<typ:paramList>N</typ:paramList>
<typ:paramList>N</typ:paramList>
<typ:paramList></typ:paramList>
</typ:submitESSJobRequest>
</soapenv:Body>
</soapenv:Envelope>"""

    r = post_soap(endpoint, user, pwd, xml)
    if r.status_code != 200:
        raise SystemExit(f"submitESSJobRequest (Interface Loader) HTTP {r.status_code}")
    
    fault, vals = parse_fault_and_vals(r.text)
    if fault:
        raise SystemExit(f"submitESSJobRequest (Interface Loader) fault: {fault}")

    job_id = (vals.get("JobRequestIds") or [None])[0]
    if not job_id: 
        raise SystemExit("No JobRequestId returned for Interface Loader.")
    
    print(f"✅ Interface Loader submitted. JobRequestId={job_id}")
    return job_id

def submit_budget_import(transaction_id: int) -> str:
    """Submit Budget Import job"""
    base_url, user, pwd = load_env()
    endpoint = f"{base_url}/fscmService/ErpIntegrationService"

    xml = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
   <soapenv:Header/>
   <soapenv:Body>
      <typ:submitESSJobRequest>
         <typ:jobPackageName>/oracle/apps/ess/financials/commitmentControl/integration/budgetImport/</typ:jobPackageName>
         <typ:jobDefinitionName>BudgetImport</typ:jobDefinitionName>
         <!--Zero or more repetitions:-->
         <typ:paramList>HYPERION</typ:paramList>
         <typ:paramList>MIC_HQ_MONTHLY</typ:paramList>
         <typ:paramList>MIC_HQ_MONTHLY_{transaction_id}</typ:paramList>
         <typ:paramList>INCREMENT</typ:paramList>
         <typ:paramList></typ:paramList>
         <typ:paramList>ESS</typ:paramList>
         <typ:paramList>XCC</typ:paramList>
         <typ:paramList>ADJUST_BUDGET</typ:paramList>
         <typ:paramList>NA</typ:paramList>
      </typ:submitESSJobRequest>
   </soapenv:Body>
</soapenv:Envelope>"""

    r = post_soap(endpoint, user, pwd, xml)
    if r.status_code != 200:
        raise SystemExit(f"submitESSJobRequest (Budget Import) HTTP {r.status_code}")
    
    fault, vals = parse_fault_and_vals(r.text)
    if fault:
        raise SystemExit(f"submitESSJobRequest (Budget Import) fault: {fault}")

    job_id = (vals.get("JobRequestIds") or [None])[0]
    if not job_id: 
        raise SystemExit("No JobRequestId returned for Budget Import.")
    
    print(f"✅ Budget Import submitted. JobRequestId={job_id}")
    return job_id

def get_ess_status(job_request_id: str) -> str:
    """Get ESS job status"""
    base_url, user, pwd = load_env()
    endpoint = f"{base_url}/fscmService/ErpIntegrationService"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
  <soapenv:Header/>
  <soapenv:Body>
    <typ:getESSJobStatus>
      <typ:requestId>{job_request_id}</typ:requestId>
    </typ:getESSJobStatus>
  </soapenv:Body>
</soapenv:Envelope>"""

    # Try with no SOAPAction first (most common for getESSJobStatus)
    r = post_soap(endpoint, user, pwd, xml, soap_action="")
    
    if r.status_code == 200:
        fault, vals = parse_fault_and_vals(r.text)
        if not fault:
            # Look for status in results
            for result in vals.get("Results", []):
                if not result.isdigit() and result.strip():  # Non-numeric result = status
                    return result.strip()
            # If no status found but request succeeded, return "RUNNING"
            return "RUNNING"
    
    # Try alternate parameter name if first attempt failed
    xml2 = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
  <soapenv:Header/>
  <soapenv:Body>
    <typ:getESSJobStatus>
      <typ:jobRequestId>{job_request_id}</typ:jobRequestId>
    </typ:getESSJobStatus>
  </soapenv:Body>
</soapenv:Envelope>"""

    r2 = post_soap(endpoint, user, pwd, xml2, soap_action="")
    if r2.status_code == 200:
        fault, vals = parse_fault_and_vals(r2.text)
        if not fault:
            for result in vals.get("Results", []):
                if not result.isdigit() and result.strip():
                    return result.strip()
            return "RUNNING"
    
    return f"UNKNOWN (HTTP {r.status_code})"

def wait_for_job(job_id: str, job_name: str) -> bool:
    """Wait for job to complete and return success status"""
    print(f"\n⏳ Waiting for {job_name} {job_id} to complete...")
    terminal_states = {"SUCCEEDED", "ERROR", "WARNING", "CANCELLED", "FAULT"}
    
    while True:
        status = get_ess_status(job_id)
        print(f"   {job_name} status: {status}")
        
        if any(s in status for s in terminal_states):
            if "SUCCEEDED" in status:
                print(f"🎉 {job_name} SUCCEEDED!")
                return True
            else:
                print(f"❌ {job_name} ended with status: {status}")
                return False
        
        time.sleep(POLL_SECS)

def run_budget_import_flow(zip_path, transaction_id):
    """Main function to run the complete budget import flow"""
    print("🚀 Budget Import Flow: UCM Upload → Interface Loader → Budget Import")
    print("="*80)
    
    try:
        # Step 1: Upload ZIP to UCM
        print("\n📤 Step 1: Uploading file to UCM...")
        doc_id = upload_to_ucm(zip_path)
        
        # Step 2: Submit Interface Loader
        print("\n🔄 Step 2: Submitting Interface Loader...")
        loader_job_id = submit_interface_loader(doc_id)
        
        # Step 3: Wait for Interface Loader to complete
        print("\n⏳ Step 3: Waiting for Interface Loader to complete...")
        if not wait_for_job(loader_job_id, "Interface Loader"):
            raise SystemExit("Interface Loader failed. Stopping execution.")
        
        # Step 4: Submit Budget Import
        print("\n💰 Step 4: Submitting Budget Import...")
        budget_job_id = submit_budget_import(transaction_id=transaction_id)
        
        # Step 5: Wait for Budget Import to complete
        print("\n⏳ Step 5: Waiting for Budget Import to complete...")
        if wait_for_job(budget_job_id, "Budget Import"):
            print("\n🎊 Complete flow finished successfully!")
        else:
            print("\n❌ Budget Import failed.")
            
    except Exception as e:
        print(f"\n❌ Error in budget import flow: {e}")
        raise

if __name__ == "__main__":
    run_budget_import_flow()