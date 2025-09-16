import requests
import base64
import os
import json
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

# Load environment variables
load_dotenv()

def try_soap_request(base_url, username, password, soap_request, headers):
    """Try different URL patterns for the SOAP endpoint"""
    
    # First, convert REST API URL to SOAP endpoint (like the working upload_soap_fbdi.py)
    if "/fscmRestApi/resources/" in base_url:
        soap_base_url = base_url.replace("/fscmRestApi/resources/11.13.18.05", "")
    else:
        soap_base_url = base_url.rstrip("/")
    
    # Different possible URL patterns Oracle might use
    url_patterns = [
        f"{soap_base_url}/fscmService/ErpIntegrationService",
        f"{soap_base_url}/fscmService/ErpIntegrationService?WSDL",
        f"{soap_base_url}/webservices/fscmService/ErpIntegrationService",
        f"{soap_base_url}/soa-infra/services/default/ErpIntegrationService",
        f"{soap_base_url}/fscmService/ErpIntegrationServicePortType"
    ]
    
    for url in url_patterns:
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
            
            if response.status_code == 200:
                return response, url
            elif response.status_code == 404:
                print("❌ 404 - Endpoint not found")
                continue
            elif response.status_code == 415:
                print("❌ 415 - Unsupported Media Type")
                continue
            elif response.status_code == 401:
                print("❌ 401 - Authentication failed")
                return response, url  # Return to handle auth error
            else:
                print(f"❌ {response.status_code} - {response.reason}")
                print(f"Response: {response.text[:500]}")
                
        except requests.RequestException as e:
            print(f"❌ Network error: {e}")
            continue
    
    return None, None

def upload_budget_amounts():
    """
    Upload XccBudgetInterface.zip and run both Interface Loader and Import Budget Amounts jobs
    using Oracle Fusion's importBulkDataAsync service in a single call.
    """
    
    # Configuration
    base_url = os.getenv('FUSION_BASE_URL', 'https://hcbg-dev4.fa.ocs.oraclecloud.com')
    username = os.getenv('FUSION_USER', 'AFarghaly')
    password = os.getenv('FUSION_PASS')
    
    if not password:
        password = input("Enter Oracle Fusion password: ")
    
    # File to upload
    zip_file_path = r"test_upload_fbdi\GlBudgetInterface.zip"
    
    if not os.path.exists(zip_file_path):
        print(f"Error: {zip_file_path} not found!")
        return False
    
    try:
        # Read and encode the zip file
        with open(zip_file_path, 'rb') as file:
            file_content = file.read()
            base64_content = base64.b64encode(file_content).decode('utf-8')
        
        print(f"File {zip_file_path} encoded successfully (size: {len(base64_content)} chars)")
        
        # SOAP XML Template using the proven working structure
        soap_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:erp="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/" 
                  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
                  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
  <soapenv:Header/>
  <soapenv:Body>
    <typ:importBulkDataAsync>
      <typ:document>
        <erp:Content>{base64_content}</erp:Content>
        <erp:FileName>GlBudgetInterface.zip</erp:FileName>
        <erp:ContentType>zip</erp:ContentType>
        <erp:DocumentSecurityGroup>FAFusionImportExport</erp:DocumentSecurityGroup>
        <erp:DocumentAccount>fin/budgetaryControl/import</erp:DocumentAccount>
      </typ:document>
      <!-- ONE job only: Import Budget Amounts -->
      <typ:jobDetails>
        <erp:JobName>oracle/apps/ess/financials/budgetaryControl/budgetEntries,importbudgetamounts</erp:JobName>
        <!-- IMPORTANT: Parameter order must match YOUR env's "Scheduled Processes" dialog -->
        <erp:ParameterList>Budgetary Control validation,Budget revision,Hyperion Planning,MIC_HQ_MONTHLY,MIC_HQ_MONTHLY_6,Not applicable for Budgetary Control validation usage,Addition to or subtraction from current budget</erp:ParameterList>
      </typ:jobDetails>
      <typ:notificationCode>10</typ:notificationCode>
      <typ:callbackURL>#NULL</typ:callbackURL>
      <typ:jobOptions>InterfaceDetails=1,ImportOption=Y,PurgeOption=Y,ExtractFileType=ALL</typ:jobOptions>
    </typ:importBulkDataAsync>
  </soapenv:Body>
</soapenv:Envelope>"""
        
        # Headers for SOAP request (matching working structure)
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': '',
            'Accept': 'text/xml'
        }
        
        print("Jobs to be submitted:")
        print("1. Interface Loader - Load files into interface tables")
        print("2. Import Budget Amounts - Process budget data")
        
        # Try different URL patterns until we find one that works
        response, successful_url = try_soap_request(base_url, username, password, soap_request, headers)
        
        if response is None:
            print("❌ All SOAP endpoint attempts failed!")
            return False
            
        print(f"✅ Successfully connected to: {successful_url}")
        print(f"Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SOAP request successful!")
            
            # Parse the response
            try:
                # Handle MIME multipart response format
                response_text = response.text
                
                # Extract XML from MIME multipart if needed
                if "Content-Type: application/xop+xml" in response_text:
                    # Find the XML part after the MIME headers
                    xml_start = response_text.find('<?xml')
                    if xml_start == -1:
                        xml_start = response_text.find('<env:Envelope')
                    if xml_start == -1:
                        xml_start = response_text.find('<soap:Envelope')
                    
                    if xml_start != -1:
                        # Extract XML portion and clean it
                        xml_content = response_text[xml_start:]
                        # Remove any trailing MIME boundary
                        boundary_end = xml_content.find('------=_Part_')
                        if boundary_end != -1:
                            xml_content = xml_content[:boundary_end].strip()
                        response_text = xml_content
                
                print("\n📄 Processing SOAP Response...")
                
                # Save full response for debugging
                with open('soap_response.xml', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print("💾 Full response saved to: soap_response.xml")
                
                # Parse XML response
                root = ET.fromstring(response_text)
                
                # Check for Oracle faults first
                fault_elements = root.findall('.//{http://xmlns.oracle.com/oracleas/schema/oracle-fault-11_0}Fault')
                soap_faults = root.findall('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
                
                if fault_elements or soap_faults:
                    print("\n❌ Oracle Fault Detected:")
                    
                    # Extract fault details
                    for fault in fault_elements + soap_faults:
                        fault_code = fault.find('.//faultcode')
                        fault_string = fault.find('.//faultstring')
                        
                        if fault_code is not None:
                            print(f"Fault Code: {fault_code.text}")
                        if fault_string is not None:
                            print(f"Fault Message: {fault_string.text}")
                            
                            # Check for specific UCM error
                            if "FND_CMN_SERVER_CONN_ERROR" in fault_string.text:
                                print("\n🔧 UCM Connection Error Detected:")
                                print("- Oracle cannot connect to the UCM (Universal Content Management) server")
                                print("- This might be a temporary Oracle system issue")
                                print("- Contact your Oracle administrator if this persists")
                    
                    return False
                
                # Find job IDs and document ID for successful responses
                document_ids = []
                job_ids = []
                
                # Look for various response elements
                for elem in root.iter():
                    if 'DocumentId' in elem.tag:
                        document_ids.append(elem.text)
                    elif 'JobRequestId' in elem.tag:
                        job_ids.append(elem.text)
                    elif 'result' in elem.tag.lower() and elem.text and elem.text.isdigit():
                        job_ids.append(elem.text)
                
                print("\n📄 Response Details:")
                if document_ids:
                    print(f"Document ID: {document_ids[0]}")
                
                if job_ids:
                    print(f"✅ Job IDs submitted: {job_ids}")
                    print("\n📊 Monitor these jobs in Oracle ESS Console:")
                    print("Navigator → Scheduled Processes")
                    for i, job_id in enumerate(job_ids, 1):
                        job_name = "Interface Loader" if i == 1 else "Import Budget Amounts"  
                        print(f"Job {i} ({job_name}): {job_id}")
                    return True
                else:
                    print("No job IDs found in response - check soap_response.xml for details")
                    return False
                
            except ET.ParseError as e:
                print(f"❌ Error parsing XML response: {e}")
                print("Raw response (first 1000 chars):")
                print(response.text[:1000])
                
                # Try to extract readable error message
                if "faultstring" in response.text:
                    import re
                    fault_match = re.search(r'<faultstring>(.*?)</faultstring>', response.text, re.DOTALL)
                    if fault_match:
                        print(f"\n🔍 Extracted Error: {fault_match.group(1)}")
                
                return False
                
        else:
            print(f"❌ SOAP request failed with status: {response.status_code}")
            print("Response headers:", dict(response.headers))
            print("Response content:")
            print(response.text[:2000] + "..." if len(response.text) > 2000 else response.text)
            
            # Check for common errors
            if "FUN-720397" in response.text:
                print("\n🔒 Permission Error: You may not have permissions for 'Import Budget Amounts' job")
                print("Contact your Oracle administrator to add you to the required role")
            elif "authentication" in response.text.lower():
                print("\n🔑 Authentication Error: Check your username and password")
            
            return False
            
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def create_sample_env():
    """Create a sample .env file with required variables"""
    env_content = """# Oracle Fusion Configuration
ORACLE_FUSION_URL=https://hcbg-dev4.fa.ocs.oraclecloud.com
ORACLE_USERNAME=AFarghaly
ORACLE_PASSWORD=your_password_here
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    print("📝 Created sample .env file. Please update with your credentials.")

if __name__ == "__main__":
    print("🚀 Oracle Fusion Budget Import - Bulk Upload")
    print("=" * 50)
    
    # Check if .env exists
    if not os.path.exists('.env'):
        create_sample_env()
        print("Please update the .env file with your credentials and run again.")
        exit(1)
    
    # Run the upload
    success = upload_budget_amounts()
    
    if success:
        print("\n✅ Process completed successfully!")
        print("Monitor the job progress in Oracle ESS Console.")
    else:
        print("\n❌ Process failed. Check the errors above.")
    
    input("\nPress Enter to exit...")  