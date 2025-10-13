import requests
import json
import base64
import os

# =========================
# CONFIGURATION
# =========================
# Enter your credentials here
USERNAME = "AFarghaly"  # Replace with your username
PASSWORD = "Mubadala345"  # Enter your password here

# Access token
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU5OTIwNjg4LCJpYXQiOjE3NTk5MTg4ODgsImp0aSI6ImE2YzNjZWExNmM2NDRkZDNhNDg3MDY5NDgxMmFmNTA5IiwidXNlcl9pZCI6IjUifQ.C7N4Gi1HO6IEa10OiFYPDLKhcPryk8MvLn7VxImHyU4"

# API endpoint
API_URL = "https://hcbg-dev4.fa.ocs.oraclecloud.com/fscmRestApi/resources/11.13.18.05/invoices"



def send_with_basic_auth(json_data):
    """
    Send request using Basic Authentication (Username + Password)
    """
    print("\n=== Sending request with Basic Authentication ===")
    
    headers = {
        "Content-Type": "application/vnd.oracle.adf.resourceitem+json",
        "Accept": "application/json"
    }
    
    try:
        response = requests.post(
            API_URL,
            auth=(USERNAME, PASSWORD),
            headers=headers,
            json=json_data,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code in [200, 201]:
            print("\n✓ Success! Invoice created successfully.")
            return {
                "status": "success",
                "status_code": response.status_code,
                "response_body": response.json(),
                "response_headers": dict(response.headers)
            }
        else:
            print(f"\n✗ Error: Request failed with status {response.status_code}")
            return {
                "status": "error",
                "status_code": response.status_code,
                "response_body": response.text,
                "response_headers": dict(response.headers),
                "error": response.text
            }
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Exception occurred: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Network or connection error occurred"
        }


def add_base64_attachment_to_invoice(base64_content, filename, invoice_json, category="From Supplier"):
    """
    Add a base64 encoded PDF attachment to an invoice JSON object.
    Both filename and title will be the same (filename without extension).
    
    Args:
        base64_content (str): Base64 encoded PDF content
        filename (str): Name of the file (e.g., "invoice_001.pdf")
        invoice_json (dict): Complete invoice JSON object to modify
        category (str): Category of the attachment (default: "From Supplier")
        
    Returns:
        dict: Modified invoice JSON with attachment added
        
    Example:
        invoice_data = {...}  # Your invoice JSON
        base64_pdf = "JVBERi0xLjQK..."
        updated_invoice = add_base64_attachment_to_invoice(
            base64_content=base64_pdf,
            filename="invoice_12345.pdf",
            invoice_json=invoice_data
        )
    """
    print(f"\n=== Adding Base64 Attachment to Invoice JSON ===")
    
    # Get title from filename (remove .pdf extension)
    file_title = filename.replace('.pdf', '').replace('.PDF', '')
    
    # Create attachment object
    attachment = {
        "Type": "File",
        "FileName": filename,
        "Title": file_title,
        "Description": f"Invoice attachment: {filename}",
        "Category": category,
        "FileContents": base64_content
    }
    
    # Add attachment to the invoice JSON
    # If 'attachments' key doesn't exist, create it
    if "attachments" not in invoice_json:
        invoice_json["attachments"] = []
    
    # Append the new attachment (or replace if you want only one)
    invoice_json["attachments"] = [attachment]  # Replace with single attachment
    # OR use this to append: invoice_json["attachments"].append(attachment)
    
    print(f"✓ Attachment added to invoice JSON")
    print(f"  Filename: {filename}")
    print(f"  Title: {file_title}")
    print(f"  Category: {category}")
    print(f"  Base64 length: {len(base64_content)} characters")
    
    return invoice_json


def send_request(json_data="",base64_content="", filename="",title="", description="", category="From Supplier"):
    """
    Send request using either Basic Auth or Bearer Token based on availability
    """


    json_data=add_base64_attachment_to_invoice(base64_content, filename, json_data, category=category)
    if USERNAME and PASSWORD:
        return send_with_basic_auth(json_data)


