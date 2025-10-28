"""
Test file for accessing Google Gemini 2.0 Flash API
"""

import google.generativeai as genai
import os
from dotenv import load_dotenv
from pathlib import Path
import PyPDF2

# Load environment variables
load_dotenv()


def extract_text_from_pdf(pdf_file) -> str:
    """
    Extract raw text content from PDF file using PyPDF2
    
    Args:
        pdf_file: Can be either:
                  - String path to PDF file
                  - File-like object (from request.FILES, io.BytesIO, etc.)
        
    Returns:
        Extracted text as string
    """
    print("Extracting text from PDF...")
    
    try:
        text_content = []
        
        # Check if it's a file path (string) or file object
        if isinstance(pdf_file, str):
            # It's a file path
            pdf_path = Path(pdf_file)
            if not pdf_path.exists():
                print(f"Error: PDF file not found at {pdf_file}")
                return None
            print(f"Reading from path: {pdf_path.name}")
            with open(pdf_file, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                print(f"Total pages: {total_pages}")
                
                for page_num in range(total_pages):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    text_content.append(text)
                    print(f"✓ Extracted page {page_num + 1}/{total_pages}")
        else:
            # It's a file object (from Django request.FILES, etc.)
            print("Reading from file object...")
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(pdf_reader.pages)
            print(f"Total pages: {total_pages}")
            
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                text_content.append(text)
                print(f"✓ Extracted page {page_num + 1}/{total_pages}")
        
        full_text = "\n\n".join(text_content)
        print(f"\n✓ Successfully extracted {len(full_text)} characters")
        return full_text
        
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


import os
from openai import OpenAI
import google.generativeai as genai

def process_pdf_with_ai(pdf_file, user_prompt: str, model_choice: str = "gemini"):
    """
    Process PDF using either Google Gemini or DeepSeek model.
    
    Args:
        pdf_file: File path or file-like object (e.g., request.FILES)
        user_prompt: Custom question or instruction for AI
        model_choice: "gemini" or "deepseek"
    """
    # Step 1: Extract text
    print("=" * 60)
    print("STEP 1: Extracting text from PDF")
    print("=" * 60)
    
    pdf_text = extract_text_from_pdf(pdf_file)
    if not pdf_text:
        print("❌ Failed to extract text from PDF")
        return None
    
    # Combine PDF text + user prompt
    full_prompt = f"""Here is the content extracted from a PDF document:

---PDF CONTENT START---
{pdf_text}
---PDF CONTENT END---

{user_prompt}
"""

    # Step 2: Choose model
    print("\n" + "=" * 60)
    print(f"STEP 2: Processing with model => {model_choice.upper()}")
    print("=" * 60)

    # ========== GEMINI ==========
    if model_choice.lower() == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyCn41qN4bXyq5C0mUSojeJeJZ_eKZDe7q8")
        genai.configure(api_key=api_key)

        model_name = "gemini-2.0-flash-exp"
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.1)
            )
            print("✅ Gemini Response:")
            print(response.text)
            return response.text
        except Exception as e:
            print(f"❌ Gemini API Error: {e}")
            return None

    # ========== DEEPSEEK ==========
    elif model_choice.lower() == "deepseek":
        api_key = "sk-10a67facfda84d9d9f2829e5cf9ed10f"
        if not api_key:
            print("❌ Error: DEEPSEEK_API_KEY not set in environment variables")
            return None

        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": full_prompt},
                ],
                stream=False
            )

            ai_response = response.choices[0].message.content
            print("✅ DeepSeek Response:")
            print(ai_response)
            return ai_response
        except Exception as e:
            print(f"❌ DeepSeek API Error: {e}")
            return None

    # ========== INVALID MODEL ==========
    else:
        print(f"❌ Invalid model choice: {model_choice}. Use 'gemini' or 'deepseek'.")
        return None



def extract_invoice_with_gemini(pdf_file, model_name: str = "gemini-2.0-flash"): 
    """
    Extract structured invoice data using Google Gemini 2.5 Pro with Account Code Prediction
    
    Args:
        pdf_file: Can be either:
                  - String path to PDF file
                  - File-like object (from request.FILES, io.BytesIO, etc.)
        model_name: Gemini model name (default: gemini-2.0-flash-exp)
    """
    
    invoice_prompt = """
You are a PROFESSIONAL INVOICE DATA EXTRACTION AND CLASSIFICATION SPECIALIST operating in **STRICT VALUE PRESERVATION MODE**.

==============================
📊 ACCOUNT CODE CLASSIFICATION
==============================
You have access to the following Chart of Accounts. You must:
1. Analyze the OVERALL invoice description and purpose
2. Match it to the MOST APPROPRIATE account code from the list below
3. Add the "AccountCode" field ONLY at the invoice header level (NOT in line items)
4. Add the "AccountDescription" field ONLY at the invoice header level (NOT in line items)


**AVAILABLE ACCOUNT CODES:**

5000000 - Expenses (General business operating expense)
5010000 - Cost Of Sales (General business operating expense)
5010001 - Salaries Eng Staff (Employee-related operational expense)
5010002 - Depreciation Charges To Cost Of Sales (Asset wear and tear) 
5010003 - Inventory - NRV Adjustment to PL (Inventory adjustments)
5010004 - FM Service Charges (Facility management services)
5010005 - Community Service Charges (Shared facility costs)
5010006 - Chilled Water Consumption Charges (Utility costs - water/cooling)
5010007 - Broker comission (Broker/agent fees)
5010008 - Development Fee (Development-related costs)
5010015 - Other Cost of Sales (Miscellaneous operational costs)
5010016 - Other Cost of Sales - RP (Miscellaneous operational costs)
5040000 - General And Administrative Expenses (General overhead)
5040100 - G&A - Staff Costs (General staff-related costs)
5040101 - Basic Salary (Employee base pay)
5040102 - Children Allowance (Employee family benefits)
5040103 - Social Allowance (Employee social benefits)
5040104 - Special Allowance (Special employee benefits)
5040105 - Airfare Allowance (Travel/airfare benefits)
5040106 - Consolidated Allowance (Combined employee benefits)
5040107 - Overtime Expenses (Overtime pay)
5040108 - Education Assistance (Training/education)
5040109 - Life Insurance Expense (Life insurance premiums)
5040111 - Health Insurance Expense (Health insurance premiums)
5040112 - Leave Provision (Leave liability provision)
5040113 - Expatriates EOSB (End of service benefits - expats)
5040114 - UAE Nationals EOSB Non Pensionable (UAE end of service)
5040115 - Defined Benefit Contribution (Pension/retirement contributions)
5040116 - UAE Nationals Pension (UAE pension)
5040117 - Employee Relocation Expenses (Relocation costs)
5040118 - Repatriation Expense (Repatriation costs)
5040119 - Non UAE Employee Pension (Non-UAE pension)
5040121 - Special Needs Assistance (Special needs support)
5040122 - Payroll Taxes Employer (Payroll taxes)
5040123 - Workers Compensation Expense (Workers compensation)
5040124 - Visa Expenses (Visa/immigration fees)
5040125 - Professional Membership Fees (Professional memberships)
5040126 - International Assignment Allowance (International assignment pay)
5040127 - Outward Secondee Compensation Recharges (Secondment costs)
5040128 - Inward Secondee Compensation Recharges (Secondment costs)
5040129 - Secondee Employee Tax Expense (Secondment taxes)
5040131 - Long-Term Contractors (Contractor costs)
5040132 - Recruitment Expenses (Hiring/recruitment costs)
5040133 - Training Expenses Fees (Training/development)
5040134 - Lump Sum Adjustments (Adjustment entries)
5040135 - Ex Gratia Payment (Discretionary payments)
5040136 - Discretionary Bonus (Performance bonuses)
5040137 - Board And Committee Membership Fee (Board/committee fees)
5040138 - Long-Term Incentive Plan Expense (Long-term incentives)
5040141 - Special Compensation Payment (Special compensation)
5040200 - G&A - Depreciation Of Property, Plant And Equipment (Asset depreciation)
5040201 - Depreciation Expense Buildings (Building depreciation)
5040202 - Depreciation Expense Machinery And Equipment (Equipment depreciation)
5040203 - Depreciation Expense Transportation Equipment (Vehicle depreciation)
5040204 - Depreciation Expense Furniture And Fixtures (Furniture depreciation)
5040205 - Depreciation Expense Office Equipment (Office equipment depreciation)
5040206 - Depreciation Expense Computers And Software (IT/software depreciation)
5040207 - Depreciation Expense Leasehold Improvements (Leasehold improvement depreciation)
8888888 - Dummy Account (General/test expense)

**CLASSIFICATION RULES:**
- Analyze the overall invoice purpose and description
- Match based on primary expense category (e.g., "salary" → 5040101, "insurance" → 5040111, "office supplies" → 5040000)
- If description mentions specific categories like "airfare", "visa", "recruitment", use that specific account
- For general office/administrative items, use 5040000 (General And Administrative Expenses)
- For cost of goods/sales items, use 5010000 or 5010015
- If completely unclear, use 5000000 (General Expenses) as fallback
- **IMPORTANT:** Add "AccountCode" field ONLY at invoice header level (top), NOT in each line item

==============================
🎯 CORE OBJECTIVE
==============================
Your objectives are:
1. EXTRACT DATA **EXACTLY AS IT APPEARS** in the invoice
2. CLASSIFY the invoice with ONE appropriate AccountCode at the header level

==============================
🎯 CORE OBJECTIVE
==============================
Your sole objective is to EXTRACT DATA **EXACTLY AS IT APPEARS** in the provided invoice document.

- Copy all text verbatim — preserving **case, spacing, punctuation, currency symbols, minus signs, separators, and decimals**.  
- **NEVER** guess, normalize, reformat, calculate, or infer EXCEPT for verifying that the InvoiceAmount equals the total of line item amounts (see rules below).  
- If a value does not explicitly appear, return `"Not Found"` (or `"N/A"` only if the invoice literally shows `"N/A"`).  
- Output must be **syntactically valid JSON** — no extra text, markdown, or explanation.

==============================
📜 SOURCE-OF-TRUTH
==============================
- Use ONLY the contents of the provided invoice (all pages).  
- Ignore prior knowledge, assumptions, or external references.  
- Apply the same extraction logic whether the document is an invoice, pro forma, receipt, quote, or credit note.  
- Missing or unreadable values must be `"Not Found"`.  

==============================
🔎 FIELD RECOGNITION (Synonyms)
==============================
Use the following labels to locate fields, but DO NOT modify the extracted text:

- **PO Number:** “PO”, “P.O.”, “Purchase Order”, “Purchase Order No.”, “Order No.”, “LPO”  
- **Supplier Name:** “Supplier”, “Vendor”, “Company”, “From”, or the letterhead/company name  
- **Invoice Number:** “Invoice No.”, “Invoice#”, “Invoice #”, “Inv No.”, “Bill No.”  
- **Invoice Total Amount (Grand Total):** “Grand Total”, “Total”, “Total Due”, “Amount Due”, “Invoice Total”, “Balance Due”  
- **Invoice Date:** “Invoice Date”, “Date”  
- **Payment Term:** “Payment Terms”, “Terms”, “Due on Receipt”, “Net 7/10/15/30/60”, “COD”  
- **Vendor TRN/VAT/Tax Reg No.:** “TRN”, “Tax Registration Number”, “VAT No.”, “VAT Reg No.”, “Tax ID”, “TIN”, “GSTIN”, “ABN”, “EIN”  
  (Only use if clearly labeled for the vendor.)

==============================
📦 LINE ITEM EXTRACTION
==============================
- Extract every billable line item across all pages in the **original document order**.  
- Multiline descriptions must preserve line breaks using `\\n`.  
- Tax rate per line must be copied exactly if shown; if only a global tax is given, set `"tax_rate": "Not Found"`.  
- Line Amount must include the currency symbol only if it appears on that line.  
  - Do not add or assume a currency symbol that isn’t printed there.

==============================
⚖️ CONFLICT / TIE-BREAK RULES
==============================
If multiple candidates exist:
- **Invoice Number / Date:** Prefer the value nearest to a heading labeled “Invoice”.  
- **Invoice Total Amount:** Prefer “Grand Total” or “Total Due”. If both exist, choose the **final payable Total Due**.  
- **Supplier Name:** Prefer the letterhead/company name or field labeled “Supplier” or “Vendor”.  
If duplicates conflict, choose the **most prominent or final payable** one. Never sum or alter.

==============================
🧩 FORMATTING & DATA INTEGRITY RULES
==============================
1. **Dates:**  
   - Keep the exact format from the document if valid.  
   - If ambiguous or nonstandard, convert to **YYYY-MM-DD** (e.g., `"2024-02-03"`).  
   - Do NOT output text-based month formats like `"Feb 03, 2024"`.
   - Dont make it like this "2024-02-00", for example it should be "2024-02-01" even if the date is shown 00 .

2. **Amounts & Numbers:**  
   - Preserve original format, including symbols and separators.  
   - **Never include spaces inside numeric values** — `"56423. 20"` → ❌ must be `"56423.20"` ✅.  
   - Apply this rule to all numeric fields (totals, taxes, line items, etc.).
   - make sure "DistributionLineNumber" is incremented by 1 for each line item, starting from 1.

3. **InvoiceAmount Rule:**  
   - `"InvoiceAmount"` must **equal the total sum of all `"LineAmount"` values** from `"invoiceLines"`.  
   - If a labeled “Grand Total”, “Total Due”, or “Invoice Total” appears, use that exact figure **and confirm it equals the sum of line items**.  
   - If no explicit total is shown, compute `"InvoiceAmount"` as the arithmetic sum of all `"LineAmount"` values **exactly as printed** (no rounding or reformatting).  
   - If mismatch occurs, still copy the total from the document but log `"Not Found"` if no total field exists.

4. **Whitespace:**  
   - Preserve internal spacing within text fields.  
   - Trim only outer spaces that would break JSON.

5. **JSON Output:**  
   - Must be valid JSON only.  
   - No markdown, commentary, or explanation.

==============================
📤 REQUIRED OUTPUT SCHEMA
==============================
Return exactly this JSON structure (no additional or missing fields):

{
  "InvoiceNumber": "85151151656498798",
  "InvoiceCurrency": "AED",
  "InvoiceAmount": 2212.75,
  "InvoiceDate": "2019-02-01",
  "BusinessUnit": "MIC Headquarter BU",
  "Supplier": "ABEER SHEIKH",
  "SupplierSite": "DUBAI",
  "InvoiceGroup": "01Feb2019",
  "Description": "Office Supplies",
  "AccountCode": "5040000",
  "Account Description": "General And Administrative Expenses",

  "invoiceDff": [{
    "__FLEX_Context": "MIC_HQ"
  }],

  "invoiceLines": [{
    "LineNumber": 1,
    "LineAmount": 2112.75,

    "invoiceLineDff": [{
      "__FLEX_Context": "MIC_HQ"
    }],

    "invoiceDistributions": [{
      "DistributionLineNumber": 1,
      "DistributionLineType": "Item",
      "DistributionAmount": 2112.75,
      "DistributionCombination": "10001-B030001-5010015-M0000-UAECE01-00000-000000-000000-000000"
    }]
  }]
}

==============================
✅ VALIDATION BEFORE RETURN
==============================
Before returning the JSON:
1. Ensure every expected field exists — use `"Not Found"` if missing.  
2. Confirm valid JSON (no trailing commas, quotes, or bracket errors).  
3. Include all line items from the document in `"invoiceLines"`, in order.  
4. Verify `"InvoiceAmount"` equals the **sum of all `"LineAmount"` values**.  
5. If an explicit total is shown on the document, copy that exact value (verbatim) and ensure it matches the sum.  
6. Do not perform any math other than summing `"LineAmount"` values exactly as shown.  
7. Do not infer, round, or normalize amounts.  
8. Always preserve these fixed values exactly:
   - `"DistributionCombination": "10001-B030001-5010015-M0000-UAECE01-00000-000000-000000-000000"`
   - `"invoiceLineDff": [{ "__FLEX_Context": "MIC_HQ" }]`
   - `"BusinessUnit": "MIC Headquarter BU"`
   - `"Supplier": "ABEER SHEIKH"`
   - `"SupplierSite": "DUBAI"`
9. All numeric fields (totals, taxes, lines) must have **no spaces** inside numbers or decimals.
10. Dates must appear as **YYYY-MM-DD**.
11. "DistributionAmount value is same as LineAmount value.
12. Dont ignore any 0 like if 300.20 keep keep it 300.20 not 300.
13. InvoiceAmount should = the total of all LineAmount values.
14. **Add "AccountCode" field at invoice header level ONLY** - analyze the overall invoice description/purpose and assign the most appropriate account code from the provided list.
15. Do NOT add AccountCode to individual line items.

==============================
🚫 OUTPUT RESTRICTIONS
==============================
- Return **only** the valid JSON object — no markdown or text.  
- Do **not** infer or enrich missing data.  
- Maintain all explicitly provided fixed values exactly as stated.  
- `"InvoiceAmount"` must always equal the total of all line item `"LineAmount"` values (verbatim).
- AccountCode appears ONLY at the invoice header level (top), NOT in line items.
-  "data": {
        "InvoiceNumber": "INVABU -0000 -2025",
        "InvoiceCurrency": "AED",
        "InvoiceAmount": "58423.40",
        "InvoiceDate": "2024-09-01",
        "BusinessUnit": "MIC Headquarter BU",
        "Supplier": "ABEER SHEIKH",
        "SupplierSite": "DUBAI",
        "InvoiceGroup": "01Feb2019",
        "Description": "Office Supplies",
        "AccountCode": "5040000",
        "Account Description": "General And Administrative Expenses",
        "invoiceDff": [
            {
                "__FLEX_Context": "MIC_HQ"
            }
        ],
        "invoiceLines": [
            {
                "LineNumber": 1,
                "LineAmount": "56423.20",
                "invoiceLineDff": [
                    {
                        "__FLEX_Context": "MIC_HQ"
                    }
                ],
                "invoiceDistributions": [
                    {
                        "DistributionLineNumber": 1,
                        "DistributionLineType": "Item",
                        "DistributionAmount": "56423.20",
                        "DistributionCombination": "10001-B030001-5010015-M0000-UAECE01-00000-000000-000000-000000"
                    }
                ]
            },
            {
                "LineNumber": 2,
                "LineAmount": "2000.20",
                "invoiceLineDff": [
                    {
                        "__FLEX_Context": "MIC_HQ"
                    }
                ],
                "invoiceDistributions": [
                    {
                        "DistributionLineNumber": 2,
                        "DistributionLineType": "Item",
                        "DistributionAmount": "2000.20",
                        "DistributionCombination": "10001-B030001-5010015-M0000-UAECE01-00000-000000-000000-000000"
                    }
                ]
            }
        ]
    } this is wrong because InvoiceAmount not equal the total of all LineAmount values. it should be 58423.40
"""

    
    return process_pdf_with_ai(pdf_file, invoice_prompt, model_name)


if __name__ == "__main__":
    print("=" * 60)
    print("PDF Processing: Google Gemini 2.5 Pro")
    print("=" * 60)
    print()

    extract_invoice_with_gemini(r"Invoice\AI\Invoice - 1000015371z.pdf")

