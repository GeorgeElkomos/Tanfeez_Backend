import os

import base64

import requests

import zipfile

import time

from dotenv import load_dotenv

load_dotenv()

def _env(primary, fallback=None, default=None):

    """

    Read env using either FUSION_* or ORACLE_* keys.

    """

    val = os.getenv(primary)

    if val: return val

    if fallback: 

        val = os.getenv(fallback)

        if val: return val

    return default

# ---------- Configuration (via .env) ----------

BASE_URL = _env('FUSION_BASE_URL', 'ORACLE_FUSION_URL')

USER     = _env('FUSION_USER',      'ORACLE_USERNAME')

PASS     = _env('FUSION_PASS',      'ORACLE_PASSWORD')

MODE     = os.getenv('MODE', 'GL').upper()          # GL or XCC

ASYNC    = os.getenv('ASYNC', 'false').lower() in ('1','true','yes','y')

POLL     = os.getenv('POLL', 'true').lower() in ('1','true','yes','y')

SECURITY_GROUP = os.getenv('SECURITY_GROUP', 'FAFusionImportExport')

if MODE == 'GL':

    # --- General Ledger Budgets ---
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_zip_path = os.path.join(script_dir, '..', 'GlBudgetInterface.zip')
    ZIP_PATH   = os.getenv('ZIP_PATH', default_zip_path)

    FILE_NAME  = os.getenv('FILE_NAME', 'GlBudgetInterface.zip')

    DOC_ACCOUNT= os.getenv('DOC_ACCOUNT', 'fin/generalLedgerBudgetBalance/import')

    JOB_NAME   = '/oracle/apps/ess/financials/commonModules/shared/common/interfaceLoader;InterfaceLoaderController'

    IMPORT_PROCESS_CODE = os.getenv('GL_IMPORT_PROCESS_CODE')

    if not IMPORT_PROCESS_CODE:

        raise RuntimeError(

            "Set GL_IMPORT_PROCESS_CODE in .env to the loader's Argument1 "

            '(the code behind "Validate and Upload Budgets").'

        )

    PARAM_LIST = f'{IMPORT_PROCESS_CODE},#NULL,N,N'  # Arg2 #NULL -> service injects uploaded DocumentId

elif MODE == 'XCC':

    # --- Budgetary Control (XCC) + GL ---

    ZIP_PATH   = os.getenv('ZIP_PATH', r'test_upload_fbdi\GlBudgetInterface.zip')

    FILE_NAME  = os.getenv('FILE_NAME', 'GlBudgetInterface.zip')

    DOC_ACCOUNT= os.getenv('DOC_ACCOUNT', 'fin/budgetaryControl/import')

    # NOTE: delimiter is a SEMICOLON between package and job!

    JOB_NAME   = '/oracle/apps/ess/financials/budgetaryControl/budgetEntries;ImportBudgetAmounts'

    # Provide the exact comma-separated parameter list for your pod (as you used in UI)

    PARAM_LIST = os.getenv('XCC_PARAMETER_LIST')  # e.g. "Budgetary Control validation,Budget revision,Hyperion Planning,MY_BUDGET,MY_LEDGER,Not applicable...,Addition to or subtraction from current budget"

    if not PARAM_LIST:

        raise RuntimeError("Set XCC_PARAMETER_LIST in .env to the comma-separated parameters for Import Budget Amounts.")

else:

    raise RuntimeError("MODE must be 'GL' or 'XCC'.")

# SOAP endpoint (POST here; do NOT post to ?WSDL)

ENDPOINT = BASE_URL.rstrip('/') + '/fscmService/ErpIntegrationService'

# ---------- Helpers ----------

def validate_zip_contains(path, expected_csv):

    if not os.path.exists(path):

        raise FileNotFoundError(f'ZIP not found: {path}')

    with zipfile.ZipFile(path, 'r') as z:

        names = [n.split('/')[-1] for n in z.namelist()]

        if expected_csv not in names:

            raise RuntimeError(f"ZIP must contain '{expected_csv}'. Found: {names}")

def build_import_envelope(b64, file_name, doc_account, job_name, param_list, async_call=False,

                          security_group=SECURITY_GROUP, document_title=None, document_name=None):

    op = 'importBulkDataAsync' if async_call else 'importBulkData'

    if not document_title: document_title = file_name.rsplit('.', 1)[0]

    if not document_name: document_name = document_title

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"

  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/"

  xmlns:erp="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/">
<soapenv:Header/>
<soapenv:Body>
<typ:{op}>
<typ:document>
<erp:Content>{b64}</erp:Content>
<erp:FileName>{file_name}</erp:FileName>
<erp:ContentType>zip</erp:ContentType>
<erp:DocumentTitle>{document_title}</erp:DocumentTitle>
<erp:DocumentName>{document_name}</erp:DocumentName>
<erp:DocumentSecurityGroup>{security_group}</erp:DocumentSecurityGroup>
<erp:DocumentAccount>{doc_account}</erp:DocumentAccount>
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
</soapenv:Envelope>'''

def post_soap(xml_body):

    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'Accept': 'text/xml',
        'SOAPAction': ''
    }

    print(f"🔍 Sending request to: {ENDPOINT}")
    print(f"🔍 Headers: {headers}")
    print(f"🔍 Body length: {len(xml_body)} characters")
    print(f"🔍 Body preview (first 500 chars):")
    print(xml_body[:500])
    
    r = requests.post(ENDPOINT, data=xml_body, headers=headers, auth=(USER, PASS), timeout=180)

    print(f"HTTP Status: {r.status_code}")
    print(f"Response Headers: {dict(r.headers)}")
    print(f"Response Body (first 2000 chars):")
    print(r.text[:2000])
    
    if r.status_code >= 400:
        print(f"❌ Error {r.status_code}: {r.reason}")
        if "fault" in r.text.lower():
            print("🔍 SOAP Fault detected in response")
        return None
    
    return r.text

def extract_request_id(xml_text):

    import re

    # try common tags

    for tag in ('result', 'JobRequestId', 'jobRequestId', 'requestId'):

        m = re.search(fr'<{tag}>(\d+)</{tag}>', xml_text)

        if m:

            return m.group(1)

    # surface SOAP fault if present

    fault = re.search(r'<faultstring>(.*?)</faultstring>', xml_text, re.DOTALL)

    if fault:

        raise RuntimeError(f"SOAP Fault: {fault.group(1).strip()}")

    # write for debugging

    with open('soap_response.xml', 'w', encoding='utf-8') as f:

        f.write(xml_text)

    raise RuntimeError('Could not find ESS request id in response. See soap_response.xml.')

def get_status(request_id):

    body = f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"

  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
<soapenv:Header/>
<soapenv:Body>
<typ:getESSJobStatus><typ:requestId>{request_id}</typ:requestId></typ:getESSJobStatus>
</soapenv:Body>
</soapenv:Envelope>'''

    txt = post_soap(body)

    import re

    m = re.search(r'<result>([^<]+)</result>', txt)

    return m.group(1).strip() if m else txt

def download_logs(request_id, out_zip=None):

    body = f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"

  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
<soapenv:Header/>
<soapenv:Body>
<typ:downloadESSJobExecutionDetails>
<typ:requestId>{request_id}</typ:requestId>
<typ:fileType>All</typ:fileType>
</typ:downloadESSJobExecutionDetails>
</soapenv:Body>
</soapenv:Envelope>'''

    r = requests.post(ENDPOINT, data=body, auth=(USER, PASS), timeout=180)

    r.raise_for_status()

    import re

    m = re.search(r'<result>([A-Za-z0-9+/=\s]+)</result>', r.text)

    if not m:

        with open('download_details.xml', 'w', encoding='utf-8') as f:

            f.write(r.text)

        raise RuntimeError('Could not extract logs (see download_details.xml).')

    b64 = m.group(1).replace('\n', '').strip()

    if not out_zip:

        out_zip = f'ess_{request_id}_out.zip'

    with open(out_zip, 'wb') as f:

        f.write(base64.b64decode(b64))

    return out_zip

def main():

    if not BASE_URL or not USER or not PASS:

        raise RuntimeError('Set FUSION_BASE_URL, FUSION_USER, FUSION_PASS (or ORACLE_* equivalents) in .env.')

    expected_csv = 'GlBudgetInterface.csv' if MODE == 'GL' else 'XccBudgetInterface.csv'

    validate_zip_contains(ZIP_PATH, expected_csv)

    # Build and send importBulkData(/Async)

    b64 = base64.b64encode(open(ZIP_PATH, 'rb').read()).decode('utf-8')

    envelope = build_import_envelope(b64, FILE_NAME, DOC_ACCOUNT, JOB_NAME, PARAM_LIST, async_call=ASYNC)

    response_text = post_soap(envelope)
    
    if response_text is None:
        print("❌ SOAP request failed. Check the error details above.")
        return

    # Save and parse response

    with open('soap_response.xml', 'w', encoding='utf-8') as f:

        f.write(response_text)

    request_id = extract_request_id(response_text)

    print(f'ESS request id: {request_id}')

    # Optional: poll for completion and fetch logs

    if POLL:

        for i in range(60):  # up to ~10 min at 10s intervals

            status = get_status(request_id)

            print(f'[{i:02d}] status = {status}')

            if status.upper() in ('SUCCEEDED', 'SUCCESS', 'ERROR', 'WARNING', 'FAILED', 'CANCELLED'):

                break

            time.sleep(10)

        try:

            log_zip = download_logs(request_id)

            print(f'Logs saved to {log_zip}')

        except Exception as e:

            print(f'Could not download logs yet: {e}')

if __name__ == "__main__":

    print("🚀 importBulkData for Budgets (GL default)")

    main()
 