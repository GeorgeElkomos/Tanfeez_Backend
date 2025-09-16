import os, base64, requests, time, zipfile, re
from dotenv import load_dotenv

load_dotenv()

def _env(primary, fallback=None, default=None):
    v = os.getenv(primary) or (os.getenv(fallback) if fallback else None)
    return v if v is not None else default

BASE_URL = _env('FUSION_BASE_URL', 'ORACLE_FUSION_URL')
USER     = _env('FUSION_USER',      'ORACLE_USERNAME')
PASS     = _env('FUSION_PASS',      'ORACLE_PASSWORD')

MODE = os.getenv('MODE', 'XCC').upper()    # force XCC by default for this script
if MODE != 'XCC':
    print('⚠️ Forcing MODE=XCC for this script.')
    MODE = 'XCC'

ZIP_PATH      = os.getenv('ZIP_PATH', './XccBudgetInterface.zip')
FILE_NAME     = os.getenv('FILE_NAME', 'XccBudgetInterface.zip')
DOC_ACCOUNT   = os.getenv('DOC_ACCOUNT', 'fin/budgetaryControl/import')
SECURITY_GROUP= os.getenv('SECURITY_GROUP', 'FAFusionImportExport')
EXPECTED_CSV  = 'XccBudgetInterface.csv'

ENDPOINT = BASE_URL.rstrip('/') + '/fscmService/ErpIntegrationService'

def validate_zip_contains(path, expected_csv):
    if not os.path.exists(path):
        raise FileNotFoundError(f'ZIP not found: {path}')
    with zipfile.ZipFile(path, 'r') as z:
        names = [n.split('/')[-1] for n in z.namelist()]
        if expected_csv not in names:
            raise RuntimeError(f"ZIP must contain '{expected_csv}'. Found: {names}")

def build_upload_envelope(b64, file_name, doc_account, security_group):
    # Unique title/name per run avoids UCM collisions on document title
    tag = f"{int(time.time())}"
    title = f"{file_name.rsplit('.',1)[0]}_{tag}"
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/"
  xmlns:erp="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/">
  <soapenv:Header/>
  <soapenv:Body>
    <typ:uploadFileToUcm>
      <typ:document>
        <erp:Content>{b64}</erp:Content>
        <erp:FileName>{file_name}</erp:FileName>
        <erp:ContentType>zip</erp:ContentType>
        <erp:DocumentTitle>{title}</erp:DocumentTitle>
        <erp:DocumentName>{title}</erp:DocumentName>
        <erp:DocumentSecurityGroup>{security_group}</erp:DocumentSecurityGroup>
        <erp:DocumentAccount>{doc_account}</erp:DocumentAccount>
      </typ:document>
    </typ:uploadFileToUcm>
  </soapenv:Body>
</soapenv:Envelope>'''

def post_soap(xml):
    headers = {'Content-Type':'text/xml; charset=utf-8','Accept':'text/xml','SOAPAction':''}
    r = requests.post(ENDPOINT, data=xml, headers=headers, auth=(USER, PASS), timeout=180)
    if r.status_code >= 400:
        raise RuntimeError(f'HTTP {r.status_code}: {r.text[:2000]}')
    return r.text

def parse_document_id(txt):
    m = re.search(r'<result>(\d+)</result>', txt)
    if m: return m.group(1)
    f = re.search(r'<faultstring>(.*?)</faultstring>', txt, re.DOTALL)
    if f: raise RuntimeError(f'SOAP Fault: {f.group(1)}')
    raise RuntimeError(f'Could not find DocumentId in response:\n{txt[:1200]}')

def to_dollar(path):  # alternative account style for some pods
    return path.replace('/', '$') + ('$' if not path.endswith('/') else '')

def main():
    if not BASE_URL or not USER or not PASS:
        raise RuntimeError('Set FUSION_BASE_URL, FUSION_USER, FUSION_PASS in .env')
    # Resolve relative ZIP path vs script location
    zip_path = ZIP_PATH if os.path.isabs(ZIP_PATH) else os.path.normpath(os.path.join(os.getcwd(), ZIP_PATH))
    validate_zip_contains(zip_path, EXPECTED_CSV)

    b64 = base64.b64encode(open(zip_path,'rb').read()).decode('utf-8')
    # Try slash-style, then $-style, to avoid FND_CMN_SERVER_CONN_ERROR edge cases
    for account in (DOC_ACCOUNT, to_dollar(DOC_ACCOUNT)):
        try:
            body = build_upload_envelope(b64, FILE_NAME, account, SECURITY_GROUP)
            resp = post_soap(body)
            doc_id = parse_document_id(resp)
            print(f'✅ Uploaded to UCM. DocumentId = {doc_id}')
            open('last_doc_id.txt','w').write(doc_id)
            print('💾 Saved DocumentId to last_doc_id.txt')
            return
        except Exception as e:
            msg = str(e)
            print(f'⚠️ Upload with account "{account}" failed:\n{msg[:1000]}')
            if 'FND_CMN_SERVER_CONN_ERROR' in msg or 'UCM server' in msg:
                print('↻ Retrying with alternate UCM account style…')
                continue
            raise
    raise SystemExit('❌ Upload failed twice. Check roles, UCM availability, account & security group.')

if __name__ == '__main__':
    print('🚀 Step 1 (XCC): Upload XccBudgetInterface.zip to UCM')
    main()
