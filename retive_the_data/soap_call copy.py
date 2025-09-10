import requests
import base64
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape  # added for XML safety
import time
import os
import sys
import pandas as pd
from decimal import Decimal, InvalidOperation

# Add the parent directory to the Python path to import Django models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')
import django
django.setup()

# Import the model after Django setup
from account_and_entitys.models import XX_BalanceReport

starttime=time.time()

def safe_decimal_convert(value):
    """Safely convert value to Decimal, handling various input types"""
    if pd.isna(value) or value is None or value == '':
        return None
    
    try:
        # Handle scientific notation and convert to Decimal
        if isinstance(value, str):
            value = value.strip()
            if value.lower() in ['null', 'nan', '']:
                return None
        
        # Convert to float first to handle scientific notation, then to Decimal
        float_val = float(value)
        return Decimal(str(float_val))
    except (ValueError, InvalidOperation, TypeError):
        print(f"⚠️  Warning: Could not convert '{value}' to Decimal, using None")
        return None

def load_excel_to_database(excel_file_path="report.xlsx"):
    """Load Excel data into XX_BalanceReport table after clearing existing data"""
    try:
        print("📊 Starting to load Excel data into database...")
        
        # Clear all existing data from the table
        deleted_count = XX_BalanceReport.objects.all().delete()[0]
        print(f"🗑️  Deleted {deleted_count} existing records from XX_BalanceReport table")
        
        # Read Excel file with proper header handling
        # The first row contains the actual column names
        df = pd.read_excel(excel_file_path, header=0)
        
        # Check if the first row contains column headers, if so use it
        if df.iloc[0, 0] == 'CONTROL_BUDGET_NAME':
            # First data row contains the headers, use it as column names
            new_header = df.iloc[0]  # Grab the first row for the header
            df = df[1:]  # Take the data less the header row
            df.columns = new_header  # Set the header row as the df header
            df.reset_index(drop=True, inplace=True)
        
        print(f"📖 Read {len(df)} rows from Excel file")
        
        # Clean column names (remove extra spaces)
        df.columns = df.columns.str.strip()
        
        # Display column names for debugging
        print(f"📋 Excel columns: {list(df.columns)}")
        
        # Expected columns
        expected_columns = [
            'CONTROL_BUDGET_NAME', 'LEDGER_NAME', 'AS_OF_PERIOD', 'SEGMENT1', 
            'SEGMENT2', 'SEGMENT3', 'ENCUMBRANCE_YTD', 'OTHER_YTD', 'ACTUAL_YTD', 
            'FUNDS_AVAILABLE_ASOF', 'BUDGET_YTD'
        ]
        
        # Check if required columns exist
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            print(f"❌ Missing columns in Excel file: {missing_columns}")
            print(f"Available columns: {list(df.columns)}")
            return False
        
        created_count = 0
        error_count = 0
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Skip empty rows or summary rows
                if pd.isna(row['CONTROL_BUDGET_NAME']) or str(row['CONTROL_BUDGET_NAME']).strip() == '':
                    continue
                
                # Skip rows that might be totals or summaries (you can adjust this logic)
                if str(row['CONTROL_BUDGET_NAME']).strip() in ['Total', 'TOTAL', '']:
                    continue
                
                # Create model instance
                balance_report = XX_BalanceReport(
                    control_budget_name=str(row['CONTROL_BUDGET_NAME']).strip() if pd.notna(row['CONTROL_BUDGET_NAME']) else None,
                    ledger_name=str(row['LEDGER_NAME']).strip() if pd.notna(row['LEDGER_NAME']) else None,
                    as_of_period=str(row['AS_OF_PERIOD']).strip() if pd.notna(row['AS_OF_PERIOD']) else None,
                    segment1=str(row['SEGMENT1']).strip() if pd.notna(row['SEGMENT1']) else None,
                    segment2=str(row['SEGMENT2']).strip() if pd.notna(row['SEGMENT2']) else None,
                    segment3=str(row['SEGMENT3']).strip() if pd.notna(row['SEGMENT3']) else None,
                    encumbrance_ytd=safe_decimal_convert(row['ENCUMBRANCE_YTD']),
                    other_ytd=safe_decimal_convert(row['OTHER_YTD']),
                    actual_ytd=safe_decimal_convert(row['ACTUAL_YTD']),
                    funds_available_asof=safe_decimal_convert(row['FUNDS_AVAILABLE_ASOF']),
                    budget_ytd=safe_decimal_convert(row['BUDGET_YTD'])
                )
                
                balance_report.save()
                created_count += 1
                
                if created_count % 50 == 0:  # Progress indicator
                    print(f"📝 Processed {created_count} records...")
                    
            except Exception as e:
                error_count += 1
                print(f"❌ Error processing row {index + 1}: {str(e)}")
                print(f"Row data: {dict(row)}")
                continue
        
        print(f"✅ Successfully loaded {created_count} records into XX_BalanceReport table")
        if error_count > 0:
            print(f"⚠️  {error_count} rows had errors and were skipped")
            
        return True
        
    except Exception as e:
        print(f"❌ Error loading Excel data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def get_report_and_load_to_database(control_budget_name="MIC_HQ_MONTHLY"):
    """Download report from Oracle and load it into the database"""
    print(f"🚀 Starting report download and database load for: {control_budget_name}")
    
    # First, download the report
    success = get_report(control_budget_name)
    
    if success:
        # Then load it into the database
        load_success = load_excel_to_database("report.xlsx")
        
        if load_success:
            print("🎉 Report download and database load completed successfully!")
            
            # Display summary statistics
            total_records = XX_BalanceReport.objects.count()
            print(f"📊 Total records in XX_BalanceReport table: {total_records}")
            
            # Show latest records by period
            latest_periods = XX_BalanceReport.objects.values('as_of_period').distinct()[:5]
            print(f"📅 Available periods: {[p['as_of_period'] for p in latest_periods]}")
            
        else:
            print("❌ Failed to load data into database")
    else:
        print("❌ Failed to download report")

def get_report(control_budget_name):
    """Download report from Oracle service"""
    try:
        url = "https://hcbg-dev4.fa.ocs.oraclecloud.com:443/xmlpserver/services/ExternalReportWSSService"
        username = "AFarghaly"
        password = "Mubadala345"

        # New parameter value (edit as needed)
        P_CONTROL_BUDGET_NAME_VALUE = control_budget_name

        escaped_param = escape(P_CONTROL_BUDGET_NAME_VALUE)

        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
        <soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"
                       xmlns:pub="http://xmlns.oracle.com/oxp/service/PublicReportService">
           <soap12:Header/>
           <soap12:Body>
              <pub:runReport>
                 <pub:reportRequest>
                    <pub:reportAbsolutePath>/API/balancess_report.xdo</pub:reportAbsolutePath>
                    <pub:attributeFormat>xlsx</pub:attributeFormat>
                    <pub:sizeOfDataChunkDownload>-1</pub:sizeOfDataChunkDownload>
                    <pub:parameterNameValues>
                       <pub:item>
                          <pub:name>P_CONTROL_BUDGET_NAME</pub:name>
                          <pub:values>
                             <pub:item>{escaped_param}</pub:item>
                          </pub:values>
                       </pub:item>
                    </pub:parameterNameValues>
                 </pub:reportRequest>
              </pub:runReport>
           </soap12:Body>
        </soap12:Envelope>
        """

        headers = {
           "Content-Type": "application/soap+xml;charset=UTF-8"
        }

        response = requests.post(url, data=soap_body, headers=headers, auth=(username, password))

        if response.status_code == 200:
           ns = {
              "soap12": "http://www.w3.org/2003/05/soap-envelope",
              "pub": "http://xmlns.oracle.com/oxp/service/PublicReportService"
           }
           root = ET.fromstring(response.text)
           report_bytes_element = root.find(".//pub:reportBytes", ns)
           if report_bytes_element is not None and report_bytes_element.text:
              excel_data = base64.b64decode(report_bytes_element.text)
              with open("report.xlsx", "wb") as f:
                    f.write(excel_data)
              print("✅ Report saved as report.xlsx")
              return True
           else:
              print("❌ No <reportBytes> found in response")
              print(response.text)
              return False
        else:
           print(f"❌ HTTP Error {response.status_code}")
           print(response.text)
           return False
           
    except Exception as e:
        print(f"❌ Error downloading report: {str(e)}")
        return False

if __name__ == "__main__":
    # Run the complete process: download and load to database
    get_report_and_load_to_database(control_budget_name="MIC_HQ_MONTHLY")
    
    endtime = time.time()
    print(f"⏱️  Total elapsed time: {endtime - starttime:.2f} seconds")