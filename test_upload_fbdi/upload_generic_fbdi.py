# upload_generic_fbdi.py
import argparse
import base64
import os
import re
import time
from urllib.parse import urlsplit

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

# --- Env ---
BASE_URL = os.getenv("FUSION_BASE_URL")
USER = os.getenv("FUSION_USER")
PASS = os.getenv("FUSION_PASS")
DEFAULT_SECURITY_GROUP = os.getenv("SECURITY_GROUP", "FAFusionImportExport")


def _soap_endpoint_from_base(url: str | None) -> str | None:
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


def _post_soap(endpoint: str, xml_body: str, soap_action: str = "") -> str | None:
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'Accept': 'text/xml',
        'SOAPAction': soap_action,
    }
    # Persist request
    try:
        with open('generic_upload_request.xml', 'w', encoding='utf-8') as f:
            f.write(xml_body)
    except Exception:
        pass

    max_attempts = int(os.getenv('RETRY_ATTEMPTS', '3'))
    backoff_sec = float(os.getenv('RETRY_BACKOFF_SEC', '2'))

    for attempt in range(1, max_attempts + 1):
        r = requests.post(endpoint, data=xml_body, headers=headers, auth=HTTPBasicAuth(USER, PASS), timeout=180)
        ecid = r.headers.get('X-ORACLE-DMS-ECID')
        print(f"HTTP Status: {r.status_code}")
        if ecid:
            print(f"🔎 ECID: {ecid}")

        if r.status_code < 400:
            return r.text

        # Save raw response
        try:
            with open('generic_upload_raw_response.xml', 'w', encoding='utf-8') as f:
                f.write(r.text)
        except Exception:
            pass

        if r.status_code == 415 and attempt < max_attempts:
            # SOAP 1.2 retry
            ct12 = f'application/soap+xml; charset=utf-8; action="{soap_action}"'
            headers_12 = dict(headers)
            headers_12['Content-Type'] = ct12
            print(f"🔁 415: retrying SOAP 1.2: {ct12}")
            r2 = requests.post(endpoint, data=xml_body, headers=headers_12, auth=HTTPBasicAuth(USER, PASS), timeout=180)
            print(f"HTTP Status (SOAP 1.2): {r2.status_code}")
            if r2.status_code < 400:
                return r2.text
            try:
                with open('generic_upload_raw_response_soap12.xml', 'w', encoding='utf-8') as f:
                    f.write(r2.text)
            except Exception:
                pass

        if 500 <= r.status_code < 600 and attempt < max_attempts:
            sleep_for = backoff_sec * attempt
            print(f"⏳ Retrying in {sleep_for:.1f}s...")
            time.sleep(sleep_for)
            continue

        break

    return None


def _build_import_envelope(b64_content: str, file_name: str, content_type: str,
                           job_name: str, param_list: str,
                           document_account: str | None,
                           security_group: str,
                           async_call: bool) -> str:
    op = 'importBulkDataAsync' if async_call else 'importBulkData'
    doc_account_xml = f"<erp:DocumentAccount>{document_account}</erp:DocumentAccount>" if document_account else ""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/"
  xmlns:erp="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/">
  <soapenv:Header/>
  <soapenv:Body>
    <typ:{op}>
      <typ:document>
        <erp:Content>{b64_content}</erp:Content>
        <erp:FileName>{file_name}</erp:FileName>
        <erp:ContentType>{content_type}</erp:ContentType>
        <erp:DocumentTitle>{os.path.splitext(file_name)[0]}</erp:DocumentTitle>
        <erp:DocumentName>{os.path.splitext(file_name)[0]}</erp:DocumentName>
        <erp:DocumentSecurityGroup>{security_group}</erp:DocumentSecurityGroup>
        {doc_account_xml}
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


def upload_generic_fbdi(file_path: str,
                        job_package_and_name: str,
                        parameter_list: str,
                        content_type: str | None = None,
                        document_account: str | None = None,
                        security_group: str | None = None,
                        async_call: bool = True) -> dict:
    if not all([BASE_URL, USER, PASS]):
        return {"success": False, "error": "Missing FUSION_BASE_URL/FUSION_USER/FUSION_PASS"}
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    endpoint = _soap_endpoint_from_base(BASE_URL)
    if not endpoint:
        return {"success": False, "error": "Invalid SOAP endpoint derived from BASE_URL"}

    # Guess content type if not provided
    if not content_type:
        ext = os.path.splitext(file_path)[1].lower()
        content_type = 'zip' if ext == '.zip' else ('csv' if ext == '.csv' else 'octet-stream')

    sg = security_group or DEFAULT_SECURITY_GROUP

    with open(file_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')

    envelope = _build_import_envelope(
        b64_content=b64,
        file_name=os.path.basename(file_path),
        content_type=content_type,
        job_name=job_package_and_name,
        param_list=parameter_list,
        document_account=document_account,
        security_group=sg,
        async_call=async_call,
    )

    resp = _post_soap(endpoint, envelope, soap_action="")
    if resp is None:
        return {"success": False, "error": "Upload failed (see previous logs)"}

    # Persist response
    try:
        with open('generic_upload_response.xml', 'w', encoding='utf-8') as f:
            f.write(resp)
    except Exception:
        pass

    m = re.search(r'<result>(\d+)</result>', resp)
    req_id = m.group(1) if m else None
    fault = re.search(r'<faultstring>(.*?)</faultstring>', resp, re.DOTALL)
    if fault:
        return {"success": False, "error": f"SOAP Fault: {fault.group(1).strip()}", "response": resp[:2000]}
    return {"success": True, "request_id": req_id, "message": "File submitted via importBulkData"}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Upload FBDI/ZIP via importBulkData(/Async) to Oracle Fusion")
    parser.add_argument('file_path', help='Path to file (.zip/.csv)')
    parser.add_argument('--job', required=True, help='Job in format "/package;JobName"')
    parser.add_argument('--params', required=True, help='Comma-separated ParameterList string')
    parser.add_argument('--account', help='DocumentAccount (e.g. fin/generalLedgerBudgetBalance/import)')
    parser.add_argument('--secgroup', default=DEFAULT_SECURITY_GROUP, help='Document security group')
    parser.add_argument('--sync', action='store_true', help='Use importBulkData (sync) instead of async')

    args = parser.parse_args()
    result = upload_generic_fbdi(
        file_path=args.file_path,
        job_package_and_name=args.job,
        parameter_list=args.params,
        document_account=args.account,
        security_group=args.secgroup,
        async_call=not args.sync,
    )
    if result['success']:
        print(f"✅ Submitted. RequestId: {result.get('request_id', 'N/A')}")
    else:
        print(f"❌ Failed: {result['error']}")
