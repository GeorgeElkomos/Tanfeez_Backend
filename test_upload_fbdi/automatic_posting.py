#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, requests, xml.etree.ElementTree as ET, re
from dotenv import load_dotenv


def normalize_base(url: str) -> str:
    """Normalize the base URL by removing service-specific paths"""
    if not url:
        return ""
    url = url.strip().rstrip("/")
    for tok in [
        "/fscmRestApi/resources",
        "/fscmRestApi",
        "/fscmService",
        "/webservices",
        "/soa-infra",
    ]:
        i = url.find(tok)
        if i != -1:
            url = url[:i]
    return url


def load_env():
    """Load environment variables for Oracle Fusion connection"""
    load_dotenv()
    base_url = normalize_base(
        os.getenv("FUSION_BASE_URL")
        or os.getenv("ORACLE_FUSION_URL")
        or "https://hcbg.fa.em2.oraclecloud.com"  # change if you intend dev4
    )
    user = os.getenv("FUSION_USER") or os.getenv("ORACLE_USERNAME") or "AFarghaly"
    pwd = os.getenv("FUSION_PASS") or os.getenv("ORACLE_PASSWORD")
    if not pwd:
        pwd = input("Oracle Fusion password: ")
    return base_url, user, pwd


def post_soap(
    endpoint: str, user: str, pwd: str, xml: str, soap_action: str = ""
) -> requests.Response:
    """Post SOAP request to Oracle Fusion"""
    headers = {
        "Content-Type": "text/xml; charset=UTF-8",
        "Accept": "text/xml",
        "SOAPAction": soap_action,
    }
    print(f"\n➡️  POST {endpoint}  (SOAPAction: {headers['SOAPAction']!r})")
    r = requests.post(
        endpoint, data=xml, headers=headers, auth=(user, pwd), timeout=180
    )
    print("HTTP", r.status_code)
    print(r.text[:1400])
    return r


def extract_envelope(text: str) -> str | None:
    """Extract SOAP envelope from response"""
    m = re.search(r"(<(?:\w+:)?Envelope[\s\S]*?</(?:\w+:)?Envelope>)", text)
    return m.group(1) if m else None


def parse_fault_and_vals(resp_text: str):
    """Parse SOAP response for faults and extract values"""
    xml = extract_envelope(resp_text)
    if not xml:
        return "NO_SOAP_ENVELOPE_FOUND", {}
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
        return (
            f"{fc.text if fc is not None else ''} | {fs.text if fs is not None else ''}",
            {},
        )

    vals = {}
    for e in root.iter():
        t = e.tag.lower()
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


def submit_automatic_posting(ledger_id: str = "300000312635883") -> str:
    """
    Submit Automatic Posting job for General Ledger

    Args:
        ledger_id: The ledger ID to post to (default: 300000312635883)

    Returns:
        str: JobRequestId of the submitted job
    """
    base_url, user, pwd = load_env()
    endpoint = f"{base_url}/fscmService/ErpIntegrationService"

    xml = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
   <soapenv:Header/>
   <soapenv:Body>
      <typ:submitESSJobRequest>
         <typ:jobPackageName>/oracle/apps/ess/financials/generalLedger/programs/common/</typ:jobPackageName>
         <typ:jobDefinitionName>AutomaticPosting</typ:jobDefinitionName>
         <!--Zero or more repetitions:-->
         <typ:paramList>{ledger_id}</typ:paramList>
         <typ:paramList></typ:paramList>
      </typ:submitESSJobRequest>
   </soapenv:Body>
</soapenv:Envelope>"""

    print(f"🔄 Submitting Automatic Posting for Ledger ID: {ledger_id}")
    r = post_soap(endpoint, user, pwd, xml)

    if r.status_code != 200:
        raise SystemExit(
            f"submitESSJobRequest (Automatic Posting) HTTP {r.status_code}"
        )

    fault, vals = parse_fault_and_vals(r.text)
    if fault:
        raise SystemExit(f"submitESSJobRequest (Automatic Posting) fault: {fault}")

    job_id = (vals.get("JobRequestIds") or [None])[0]
    if not job_id:
        raise SystemExit("No JobRequestId returned for Automatic Posting.")

    print(f"✅ Automatic Posting submitted successfully!")
    print(f"📊 JobRequestId: {job_id}")
    return job_id


if __name__ == "__main__":
    print("🚀 Oracle Fusion Automatic Posting")
    print("=" * 50)

    # You can change the ledger ID here or pass it as parameter
    job_id = submit_automatic_posting("300000306553329")

    print(f"\n🎉 Automatic Posting job submitted with ID: {job_id}")
    print(
        "💡 You can check the job status in Oracle Fusion or use the get_ess_status function."
    )
