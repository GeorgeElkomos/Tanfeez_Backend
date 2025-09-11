"""
Utility functions for account_and_entitys app
"""
import requests
import base64
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import pandas as pd
from decimal import Decimal, InvalidOperation
from django.db import transaction
from .models import XX_BalanceReport
import json
import io


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


def download_oracle_report(control_budget_name="MIC_HQ_MONTHLY", period_name="sep-25", save_path="report.xlsx"):
    """
    Download balance report from Oracle service
    
    Args:
        control_budget_name (str): Budget name parameter for the report
        save_path (str): Path to save the downloaded Excel file
        
    Returns:
        bool: True if download successful, False otherwise
    """
    try:
        url = "https://hcbg-dev4.fa.ocs.oraclecloud.com:443/xmlpserver/services/ExternalReportWSSService"
        username = "AFarghaly"
        password = "Mubadala345"

        escaped_param = escape(control_budget_name)
        escaped_param2 = escape(period_name)

        


        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
        <soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"
                       xmlns:pub="http://xmlns.oracle.com/oxp/service/PublicReportService">
           <soap12:Header/>
           <soap12:Body>
              <pub:runReport>
                 <pub:reportRequest>
                    <pub:reportAbsolutePath>/API/period_balance_report.xdo</pub:reportAbsolutePath>
                    <pub:attributeFormat>xlsx</pub:attributeFormat>
                    <pub:sizeOfDataChunkDownload>-1</pub:sizeOfDataChunkDownload>
                    <pub:parameterNameValues>
                       <pub:item>
                          <pub:name>P_CONTROL_BUDGET_NAME</pub:name>
                          <pub:values>
                             <pub:item>{escaped_param}</pub:item>
                          </pub:values>
                       </pub:item>
                       <pub:item>
                          <pub:name>P_PERIOD_NAME</pub:name>
                          <pub:values>
                             <pub:item>{escaped_param2}</pub:item>
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
              with open(save_path, "wb") as f:
                    f.write(excel_data)
              print(f"✅ Report saved as {save_path}")
              return True
           else:
              print("❌ No <reportBytes> found in response")
              return False
        else:
           print(f"❌ HTTP Error {response.status_code}")
           return False
           
    except Exception as e:
        print(f"❌ Error downloading report: {str(e)}")
        return False


def get_oracle_report_data(control_budget_name="MIC_HQ_MONTHLY", period_name="sep-25", 
                          segment1=None, segment2=None, segment3=None):
    """
    Get balance report data directly from Oracle service for specific segment combination
    Returns data as dict/JSON without saving to file
    
    Args:
        control_budget_name (str): Budget name parameter for the report
        period_name (str): Period name parameter
        segment1 (str): Segment 1 filter parameter
        segment2 (str): Segment 2 filter parameter  
        segment3 (str): Segment 3 filter parameter
        
    Returns:
        dict: Response with success status and data
              Format: {
                  'success': bool,
                  'data': list of dict records or None,
                  'message': str,
                  'total_records': int
              }
    """
    result = {
        'success': False,
        'data': None,
        'message': '',
        'total_records': 0
    }
    
    try:
        url = "https://hcbg-dev4.fa.ocs.oraclecloud.com:443/xmlpserver/services/ExternalReportWSSService"
        username = "AFarghaly"
        password = "Mubadala345"

        escaped_param = escape(control_budget_name)
        escaped_param2 = escape(period_name)
        
        # Build parameter list - add segment filters if provided
        parameters = []
        
        # Always include the main parameters
        parameters.append(f"""
                       <pub:item>
                          <pub:name>P_CONTROL_BUDGET_NAME</pub:name>
                          <pub:values>
                             <pub:item>{escaped_param}</pub:item>
                          </pub:values>
                       </pub:item>""")
        
        parameters.append(f"""
                       <pub:item>
                          <pub:name>P_PERIOD_NAME</pub:name>
                          <pub:values>
                             <pub:item>{escaped_param2}</pub:item>
                          </pub:values>
                       </pub:item>""")
        
        # Add segment filters if provided
        if segment1:
            escaped_segment1 = escape(str(segment1))
            parameters.append(f"""
                       <pub:item>
                          <pub:name>P_SEGMENT1</pub:name>
                          <pub:values>
                             <pub:item>{escaped_segment1}</pub:item>
                          </pub:values>
                       </pub:item>""")
        
        if segment2:
            escaped_segment2 = escape(str(segment2))
            parameters.append(f"""
                       <pub:item>
                          <pub:name>P_SEGMENT2</pub:name>
                          <pub:values>
                             <pub:item>{escaped_segment2}</pub:item>
                          </pub:values>
                       </pub:item>""")
        
        if segment3:
            escaped_segment3 = escape(str(segment3))
            parameters.append(f"""
                       <pub:item>
                          <pub:name>P_SEGMENT3</pub:name>
                          <pub:values>
                             <pub:item>{escaped_segment3}</pub:item>
                          </pub:values>
                       </pub:item>""")

        parameters_xml = "".join(parameters)

        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
        <soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"
                       xmlns:pub="http://xmlns.oracle.com/oxp/service/PublicReportService">
           <soap12:Header/>
           <soap12:Body>
              <pub:runReport>
                 <pub:reportRequest>
                    <pub:reportAbsolutePath>/API/get_single_balance_report.xdo</pub:reportAbsolutePath>
                    <pub:attributeFormat>xlsx</pub:attributeFormat>
                    <pub:sizeOfDataChunkDownload>-1</pub:sizeOfDataChunkDownload>
                    <pub:parameterNameValues>{parameters_xml}
                    </pub:parameterNameValues>
                 </pub:reportRequest>
              </pub:runReport>
           </soap12:Body>
        </soap12:Envelope>
        """

        headers = {
           "Content-Type": "application/soap+xml;charset=UTF-8"
        }

        print(f"🔍 Fetching Oracle report data for segments: {segment1}, {segment2}, {segment3}")
        response = requests.post(url, data=soap_body, headers=headers, auth=(username, password))

        if response.status_code == 200:
           ns = {
              "soap12": "http://www.w3.org/2003/05/soap-envelope",
              "pub": "http://xmlns.oracle.com/oxp/service/PublicReportService"
           }
           root = ET.fromstring(response.text)
           report_bytes_element = root.find(".//pub:reportBytes", ns)
           
           if report_bytes_element is not None and report_bytes_element.text:
              # Decode the Excel data (binary, don't decode as UTF-8)
              excel_data = base64.b64decode(report_bytes_element.text)
              
              # Parse Excel data into DataFrame using BytesIO
              excel_reader = pd.read_excel(io.BytesIO(excel_data), engine='openpyxl')
              
              # Check if the first row contains column headers or if we need to skip rows
              if len(excel_reader) > 0:
                  # Check if first row has the expected columns
                  if 'CONTROL_BUDGET_NAME' not in excel_reader.columns:
                      # Try reading again, skipping the first few rows which might be title/header rows
                      for skip_rows in range(1, 5):
                          try:
                              excel_reader = pd.read_excel(io.BytesIO(excel_data), engine='openpyxl', skiprows=skip_rows)
                              if 'CONTROL_BUDGET_NAME' in excel_reader.columns:
                                  break
                          except:
                              continue
              
              # Clean column names
              excel_reader.columns = excel_reader.columns.str.strip()
              
              # Convert DataFrame to list of dictionaries
              data_list = []
              for index, row in excel_reader.iterrows():
                  # Skip empty rows or summary rows
                  if pd.isna(row.get('CONTROL_BUDGET_NAME')) or str(row.get('CONTROL_BUDGET_NAME', '')).strip() == '':
                      continue
                  
                  # Skip rows that might be totals or summaries
                  if str(row.get('CONTROL_BUDGET_NAME', '')).strip() in ['Total', 'TOTAL', '']:
                      continue
                  
                  record = {
                      'control_budget_name': str(row.get('CONTROL_BUDGET_NAME', '')).strip() if pd.notna(row.get('CONTROL_BUDGET_NAME')) else None,
                      'ledger_name': str(row.get('LEDGER_NAME', '')).strip() if pd.notna(row.get('LEDGER_NAME')) else None,
                      'as_of_period': str(row.get('AS_OF_PERIOD', '')).strip() if pd.notna(row.get('AS_OF_PERIOD')) else None,
                      'segment1': str(row.get('SEGMENT1', '')).strip() if pd.notna(row.get('SEGMENT1')) else None,
                      'segment2': str(row.get('SEGMENT2', '')).strip() if pd.notna(row.get('SEGMENT2')) else None,
                      'segment3': str(row.get('SEGMENT3', '')).strip() if pd.notna(row.get('SEGMENT3')) else None,
                      'encumbrance_ytd': float(row.get('ENCUMBRANCE_PTD', 0)) if pd.notna(row.get('ENCUMBRANCE_PTD')) and str(row.get('ENCUMBRANCE_PTD', '')).strip() != '' else 0.0,
                      'other_ytd': float(row.get('OTHER_PTD', 0)) if pd.notna(row.get('OTHER_PTD')) and str(row.get('OTHER_PTD', '')).strip() != '' else 0.0,
                      'actual_ytd': float(row.get('ACTUAL_PTD', 0)) if pd.notna(row.get('ACTUAL_PTD')) and str(row.get('ACTUAL_PTD', '')).strip() != '' else 0.0,
                      'funds_available_asof': float(row.get('FUNDS_AVAILABLE_ASOF', 0)) if pd.notna(row.get('FUNDS_AVAILABLE_ASOF')) and str(row.get('FUNDS_AVAILABLE_ASOF', '')).strip() != '' else 0.0,
                      'budget_ytd': float(row.get('BUDGET_PTD', 0)) if pd.notna(row.get('BUDGET_PTD')) and str(row.get('BUDGET_PTD', '')).strip() != '' else 0.0
                  }
                  data_list.append(record)
              
              result['success'] = True
              result['data'] = data_list
              result['total_records'] = len(data_list)
              result['message'] = f"Successfully retrieved {len(data_list)} records"
              
              print(f"✅ Successfully retrieved {len(data_list)} records from Oracle")
              return result
              
           else:
              result['message'] = "No <reportBytes> found in response"
              print("❌ No <reportBytes> found in response")
              return result
        else:
           result['message'] = f"HTTP Error {response.status_code}"
           print(f"❌ HTTP Error {response.status_code}")
           return result
           
    except Exception as e:
        result['message'] = f"Error fetching report data: {str(e)}"
        print(f"❌ Error fetching report data: {str(e)}")
        return result


def load_excel_to_balance_report_table(excel_file_path="report.xlsx", clear_existing=True):
    """
    Load Excel data into XX_BalanceReport table
    
    Args:
        excel_file_path (str): Path to the Excel file
        clear_existing (bool): Whether to clear existing data before loading
        
    Returns:
        dict: Result with success status, created count, and error details
    """
    result = {
        'success': False,
        'created_count': 0,
        'error_count': 0,
        'deleted_count': 0,
        'errors': [],
        'message': ''
    }
    
    try:
        print("📊 Starting to load Excel data into database...")
        
        with transaction.atomic():
            # Clear all existing data from the table if requested
            if clear_existing:
                deleted_count = XX_BalanceReport.objects.all().delete()[0]
                result['deleted_count'] = deleted_count
                print(f"🗑️  Deleted {deleted_count} existing records from XX_BalanceReport table")
            
            # Read Excel file with proper header handling
            df = pd.read_excel(excel_file_path, header=0)
            
            # Check if the first row contains column headers
            if df.iloc[0, 0] == 'CONTROL_BUDGET_NAME':
                # First data row contains the headers, use it as column names
                new_header = df.iloc[0]  # Grab the first row for the header
                df = df[1:]  # Take the data less the header row
                df.columns = new_header  # Set the header row as the df header
                df.reset_index(drop=True, inplace=True)
            
            print(f"📖 Read {len(df)} rows from Excel file")
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Expected columns
            expected_columns = [
                'CONTROL_BUDGET_NAME', 'LEDGER_NAME', 'AS_OF_PERIOD', 'SEGMENT1', 
                'SEGMENT2', 'SEGMENT3', 'ENCUMBRANCE_PTD', 'OTHER_PTD', 'ACTUAL_PTD', 
                'FUNDS_AVAILABLE_ASOF', 'BUDGET_PTD'
            ]
            
            # Check if required columns exist
            missing_columns = [col for col in expected_columns if col not in df.columns]
            if missing_columns:
                result['message'] = f"Missing columns: {missing_columns}"
                return result
            
            created_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    # Skip empty rows or summary rows
                    if pd.isna(row['CONTROL_BUDGET_NAME']) or str(row['CONTROL_BUDGET_NAME']).strip() == '':
                        continue
                    
                    # Skip rows that might be totals or summaries
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
                        encumbrance_ytd=safe_decimal_convert(row['ENCUMBRANCE_PTD']),
                        other_ytd=safe_decimal_convert(row['OTHER_PTD']),
                        actual_ytd=safe_decimal_convert(row['ACTUAL_PTD']),
                        funds_available_asof=safe_decimal_convert(row['FUNDS_AVAILABLE_ASOF']),
                        budget_ytd=safe_decimal_convert(row['BUDGET_PTD'])
                    )
                    
                    balance_report.save()
                    created_count += 1
                    
                    if created_count % 50 == 0:  # Progress indicator
                        print(f"📝 Processed {created_count} records...")
                        
                except Exception as e:
                    error_count += 1
                    error_detail = {
                        'row': index + 1,
                        'error': str(e),
                        'data': dict(row) if hasattr(row, 'to_dict') else str(row)
                    }
                    errors.append(error_detail)
                    continue
            
            result['success'] = True
            result['created_count'] = created_count
            result['error_count'] = error_count
            result['errors'] = errors
            result['message'] = f"Successfully loaded {created_count} records"
            
            print(f"✅ Successfully loaded {created_count} records into XX_BalanceReport table")
            if error_count > 0:
                print(f"⚠️  {error_count} rows had errors and were skipped")
            
            return result
        
    except Exception as e:
        result['message'] = f"Error loading Excel data: {str(e)}"
        print(f"❌ {result['message']}")
        return result


def refresh_balance_report_data(control_budget_name="MIC_HQ_MONTHLY", period_name="sep-25"):
    """
    Complete process: Download report from Oracle and load into database
    
    Args:
        control_budget_name (str): Budget name parameter for the report
        
    Returns:
        dict: Result with success status and details
    """
    result = {
        'success': False,
        'download_success': False,
        'load_success': False,
        'message': '',
        'details': {}
    }
    
    try:
        print(f"🚀 Starting report refresh for: {control_budget_name} (Period: {period_name})")
        
        # Step 1: Download the report
        download_success = download_oracle_report(control_budget_name, period_name, "report.xlsx")
        result['download_success'] = download_success
        
        if not download_success:
            result['message'] = "Failed to download report from Oracle"
            return result
        
        # Step 2: Load data into database
        load_result = load_excel_to_balance_report_table("report.xlsx", clear_existing=True)
        result['load_success'] = load_result['success']
        result['details'] = load_result
        
        if load_result['success']:
            result['success'] = True
            result['message'] = f"Successfully refreshed balance report data. Created {load_result['created_count']} records."
            
            # Display summary statistics
            total_records = XX_BalanceReport.objects.count()
            print(f"📊 Total records in XX_BalanceReport table: {total_records}")
            
            # Show available periods
            periods = XX_BalanceReport.objects.values_list('as_of_period', flat=True).distinct()
            print(f"📅 Available periods: {list(periods)}")
            
        else:
            result['message'] = f"Downloaded report but failed to load data: {load_result['message']}"
            
        return result
        
    except Exception as e:
        result['message'] = f"Error during report refresh: {str(e)}"
        return result
