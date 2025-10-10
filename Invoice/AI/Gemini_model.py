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


def process_pdf_with_gemini(pdf_file, user_prompt: str, model_name: str = "gemini-2.0-flash-exp"):
    """
    Process PDF using Google Gemini 2.0 Flash model
    
    Args:
        pdf_file: Can be either:
                  - String path to PDF file
                  - File-like object (from request.FILES, io.BytesIO, etc.)
        user_prompt: Your custom prompt/question about the content
        model_name: Gemini model name (default: gemini-2.0-flash-exp)
    """
    
    # Step 1: Extract text from PDF
    print("=" * 60)
    print("STEP 1: Extracting text from PDF")
    print("=" * 60)
    
    pdf_text = extract_text_from_pdf(pdf_file)
    
    if not pdf_text:
        print("Failed to extract text from PDF")
        return None
    
    # Step 2: Configure Gemini API
    print("\n" + "=" * 60)
    print(f"STEP 2: Processing with Google Gemini ({model_name})")
    print("=" * 60)
    
    api_key = "AIzaSyCOH5doSg_YSyAr8V5RSHAp0R5YbsNRP6g"
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables")
        print("Please add GEMINI_API_KEY to your .env file")
        return None
    
    genai.configure(api_key=api_key)
    
    # Combine PDF content with user's prompt
    full_prompt = f"""Here is the content extracted from a PDF document:

---PDF CONTENT START---
{pdf_text}
---PDF CONTENT END---

{user_prompt}
"""
    
    print(f"\nUsing model: {model_name}")
    print(f"User prompt: {user_prompt}")
    print("Processing with Gemini 2.0 Flash...\n")
    
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel(model_name)
        
        # Generate response
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
            )
        )
        
        print("Gemini Response:")
        print("=" * 60)
        print(response.text)
        print("=" * 60)
        print(f"\n✓ Processing complete!")
        
        return response.text
        
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        print("\nMake sure:")
        print("1. GEMINI_API_KEY is set in your .env file")
        print("2. You have a valid Google AI API key")
        print("3. The API key has access to Gemini 2.0 Flash")
        return None


def extract_invoice_with_gemini(pdf_file, model_name: str = "gemini-2.0-flash-exp"): 
    """
    Extract structured invoice data using Google Gemini 2.0 Flash
    
    Args:
        pdf_file: Can be either:
                  - String path to PDF file
                  - File-like object (from request.FILES, io.BytesIO, etc.)
        model_name: Gemini model name (default: gemini-2.0-flash-exp)
    """
    
    invoice_prompt = """
You are a PROFESSIONAL INVOICE DATA EXTRACTION SPECIALIST operating in **STRICT VALUE PRESERVATION MODE**.

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
11- "DistributionAmount value is same as LineAmount value.

==============================
🚫 OUTPUT RESTRICTIONS
==============================
- Return **only** the valid JSON object — no markdown or text.  
- Do **not** infer or enrich missing data.  
- Maintain all explicitly provided fixed values exactly as stated.  
- `"InvoiceAmount"` must always equal the total of all line item `"LineAmount"` values (verbatim).
"""

    
    return process_pdf_with_gemini(pdf_file, invoice_prompt, model_name)


if __name__ == "__main__":
    print("=" * 60)
    print("PDF Processing: Google Gemini 2.0 Flash")
    print("=" * 60)
    print()

    extract_invoice_with_gemini(r"INVABU-0000-2025 copy.pdf")
