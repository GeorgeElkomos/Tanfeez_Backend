import requests
import base64
import os
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

# Load environment variables
load_dotenv()

def try_soap_request(base_url, username, password, soap_request, headers):
    url = f"{base_url}/fscmService/ErpIntegrationService"
    print(f"\nTrying URL: {url}")
    try:
        response = requests.post(
            url,
            data=soap_request,
            headers=headers,
            auth=(username, password),
            timeout=60
        )
        print(f"Status Code: {response.status_code}")
        return response, url
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return None, None

def upload_budget_amounts():
    base_url = os.getenv('FUSION_BASE_URL', 'https://hcbg-dev4.fa.ocs.oraclecloud.com')
    username = os.getenv('FUSION_USER', 'AFarghaly')
    password = os.getenv('FUSION_PASS')

    if not password:
        password = input("Enter Oracle Fusion password: ")

    zip_file_path = r"test_upload_fbdi\XccBudgetInterface.zip"
    if not os.path.exists(zip_file_path):
        print(f"❌ File not found: {zip_file_path}")
        return False

    with open(zip_file_path, 'rb') as file:
        file_content = file.read()
        base64_content = base64.b64encode(file_content).decode('utf-8')

    print(f"File {zip_file_path} encoded successfully")

    # SOAP request with loader only (properties file in ZIP decides the job)
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
      <typ:jobDetails>
        <erp:JobName>oracle/apps/ess/financials/commonModules/shared/common/interfaceLoader,InterfaceLoaderController</erp:JobName>
      </typ:jobDetails>
      <typ:notificationCode>10</typ:notificationCode>
    </typ:importBulkDataAsync>
  </soapenv:Body>
</soapenv:Envelope>"""

    headers = {
        "Content-Type": "application/soap+xml; charset=UTF-8",
        "Accept": "text/xml"
    }

    response, successful_url = try_soap_request(base_url, username, password, soap_request, headers)
    if response is None:
        print("❌ SOAP call failed.")
        return False

    print(f"✅ Connected to: {successful_url}")
    print("Response (first 1000 chars):")
    print(response.text[:1000])

    return True

if __name__ == "__main__":
    print("🚀 Oracle Fusion Budget Import - Loader + ImportBudgetAmounts")
    print("=" * 50)
    upload_budget_amounts()
