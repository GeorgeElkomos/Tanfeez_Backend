import requests
import base64
import os
import json
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

# Load environment variables
load_dotenv()



def upload_budget_amounts():
    """
    Upload XccBudgetInterface.zip and explicitly:
      1) Run InterfaceLoader for 'Budgetary Control Budget Import' (so it picks XccBudgetInterface.ctl).
      2) Chain Import Budget Amounts in the same call.
    Also validates the ZIP layout before sending.
    """
    import zipfile

    # Configuration
    base_url = os.getenv('FUSION_BASE_URL', 'https://hcbg-dev4.fa.ocs.oraclecloud.com')
    username = os.getenv('FUSION_USER', 'AFarghaly')
    password = os.getenv('FUSION_PASS')

    if not password:
        password = input("Enter Oracle Fusion password: ")

    # File to upload
    zip_file_path = r"test_upload_fbdi\XccBudgetInterface.zip"

    # --- Pre-flight ZIP validation ---
    if not os.path.exists(zip_file_path):
        print(f"❌ ZIP not found: {zip_file_path}")
        return False

    with zipfile.ZipFile(zip_file_path, 'r') as z:
        names = z.namelist()
        print("📦 ZIP contents:", names)

        # Reject nested folders; we want root-only files
        # (zipfile stores folders as names ending with '/')
        folders = [n for n in names if n.endswith('/')]
        if folders:
            print("❌ ZIP contains subfolders. Re-zip with files at the ROOT (no folders).")
            return False

        # Must contain exactly one XccBudgetInterface.csv at root
        csv_at_root = [n for n in names if n == 'XccBudgetInterface.csv']
        if len(csv_at_root) != 1:
            print("❌ ZIP must contain exactly one file named 'XccBudgetInterface.csv' at the ROOT.")
            print("   Tip: Ensure the name is case-sensitive and there are no extra files like templates (.xlsm).")
            return False

        # Optional: warn if extra files exist
        extra = [n for n in names if n != 'XccBudgetInterface.csv']
        if extra:
            print("⚠️  Warning: Extra files detected in ZIP:", extra)
            print("    It's safer to include ONLY 'XccBudgetInterface.csv'. Proceeding anyway...")

    # Read and base64 the ZIP
    with open(zip_file_path, 'rb') as f:
        file_content = f.read()
        base64_content = base64.b64encode(file_content).decode('utf-8')

    print(f"✅ ZIP encoded (size: {len(base64_content)} chars)")

    # ---- SOAP with two jobs ----
    # 1) Force loader to Budgetary Control
    # 2) Chain Import Budget Amounts (adjust ParameterList order/values for your env if needed)
    soap_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:erp="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/"
                  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
  <soapenv:Header/>
  <soapenv:Body>
    <typ:importBulkDataAsync>
      <typ:document>
        <erp:Content>{base64_content}</erp:Content>
        <erp:FileName>XccBudgetInterface.zip</erp:FileName>
        <erp:ContentType>zip</erp:ContentType>
        <erp:DocumentSecurityGroup>FAFusionImportExport</erp:DocumentSecurityGroup>
        <erp:DocumentAccount>fin/budgetaryControl/import</erp:DocumentAccount>
      </typ:document>

        <!-- 1) Loader: force the correct import object -->
    <typ:jobDetails>
    <erp:JobName>oracle/apps/ess/financials/commonModules/shared/common/interfaceLoader,InterfaceLoaderController</erp:JobName>
    <!-- Use the EXACT UI label + FILE_ID token -->
    <erp:ParameterList>Import Budget Amounts,10015343</erp:ParameterList>
    </typ:jobDetails>

      <!-- 2) Import Budget Amounts (child) -->
      <typ:jobDetails>
        <erp:JobName>oracle/apps/ess/financials/budgetaryControl/budgetEntries,ImportBudgetAmounts</erp:JobName>
        <!-- Keep EXACT order from your Scheduled Processes UI. Use #NULL where you leave a value blank. -->
        <erp:ParameterList>Budgetary Control validation,Budget revision,Hyperion Planning,MIC_HQ_MONTHLY,MIC_HQ_MONTHLY_6,#NULL,Addition to or subtraction from current budget</erp:ParameterList>
      </typ:jobDetails>

      <typ:notificationCode>10</typ:notificationCode>
    </typ:importBulkDataAsync>
  </soapenv:Body>
</soapenv:Envelope>"""

    # Headers: avoid 415s
    headers = {
        "Content-Type": "application/soap+xml; charset=UTF-8",
        "Accept": "text/xml"
    }

    # Use the canonical endpoint
    url = f"{base_url.rstrip('/')}/fscmService/ErpIntegrationService"
    print(f"\n➡️  POST {url}")
    response = requests.post(url, data=soap_request, headers=headers, auth=(username, password), timeout=90)

    print("HTTP Status:", response.status_code)
    print(response.text[:1200])  # Trim output for readability

    if response.status_code != 200:
        return False

    # (Optional) very light parsing to surface faults quickly
    try:
        # Extract only the XML portion if the server wraps in MIME
        text = response.text
        start = text.find('<?xml')
        if start != -1:
            text = text[start:]
        root = ET.fromstring(text)
        faults = root.findall('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
        if faults:
            print("❌ SOAP Fault detected.")
            for f in faults:
                fc = f.find('faultcode')
                fs = f.find('faultstring')
                if fc is not None: print("faultcode:", fc.text)
                if fs is not None: print("faultstring:", fs.text)
            return False
    except Exception as e:
        # If parsing fails, we still printed the raw text above
        pass

    print("✅ Submitted. Check Scheduled Processes for parent (loader) and child (Import Budget Amounts) jobs.")
    return True

upload_budget_amounts()
