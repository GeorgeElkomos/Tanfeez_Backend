import argparse, os, time, zipfile, tempfile, subprocess
from pathlib import Path
import pandas as pd

def excel_to_csv_and_zip(excel_path: str, zip_path: str):
    """Convert Excel sheets to CSV files and zip them"""
    excel_file = Path(excel_path)
    
    if not excel_file.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    
    if excel_file.suffix.lower() not in ['.xlsx', '.xlsm', '.xls']:
        raise ValueError(f"File is not an Excel file: {excel_path}")
    
    # Get the directory where the ZIP file will be saved
    zip_dir = Path(zip_path).parent
    print(f"ZIP will be saved to: {zip_path}")
    print(f"CSV files will be saved to: {zip_dir}")
    
    # Read Excel file and get all sheets
    xl = pd.ExcelFile(excel_path)
    print(f"Found sheets: {xl.sheet_names}")
    
    # Create temporary CSV files first
    temp_csv_files = []
    
    try:
        for sheet_name in xl.sheet_names:
            # Skip instruction sheets
            if 'instruction' in sheet_name.lower():
                print(f"Skipping instruction sheet: {sheet_name}")
                continue
                
            try:
                # For GL_INTERFACE and XCC_BUDGET_INTERFACE sheets, headers start at row 4 (0-indexed row 3)
                if 'GL_INTERFACE' in sheet_name or 'XCC_BUDGET_INTERFACE' in sheet_name:
                    # Read without header first to get raw data
                    df_raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
                    
                    # Get ALL headers from row 4 (0-indexed row 3) - keep all 149 columns
                    all_headers = [str(df_raw.iloc[3, i]) if pd.notna(df_raw.iloc[3, i]) else f'Col_{i}' for i in range(len(df_raw.columns))]
                    
                    # Get data starting from row 5 (0-indexed row 4) - keep all columns 
                    df = df_raw.iloc[4:].copy()
                    df.columns = all_headers[:len(df.columns)]
                    
                    # DON'T drop empty columns - we want to keep all 149 columns
                    # Remove any completely empty rows only
                    df = df.dropna(how='all')
                    
                    print(f"GL_INTERFACE/XCC_BUDGET_INTERFACE: Processing all {len(df.columns)} columns, {len(df)} data rows")
                else:
                    # Try to detect header row for other sheets
                    df_temp = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
                    header_row = -1
                    max_non_null = 0
                    for i in range(min(10, len(df_temp))):
                        non_null_count = df_temp.iloc[i].notna().sum()
                        if non_null_count > max_non_null:
                            max_non_null = non_null_count
                            header_row = i
                    
                    if header_row == -1:
                        continue
                    
                    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
                
                # Special formatting for GL_INTERFACE and XCC_BUDGET_INTERFACE data BEFORE cleaning - we want ALL columns
                if 'GL_INTERFACE' in sheet_name or 'XCC_BUDGET_INTERFACE' in sheet_name:
                    # Don't clean up GL_INTERFACE data - we want all columns
                    pass
                else:
                    # Clean up the data for other sheets
                    df = df.dropna(axis=1, how='all')  # Remove empty columns
                    df = df.dropna(axis=0, how='all')  # Remove empty rows
                
                # Skip if sheet is empty
                if df.empty or len(df) == 0:
                    print(f"Skipping empty sheet: {sheet_name}")
                    continue
                
                # Special formatting for GL_INTERFACE and XCC_BUDGET_INTERFACE data to match Oracle FBDI exactly
                if 'GL_INTERFACE' in sheet_name or 'XCC_BUDGET_INTERFACE' in sheet_name:
                    # Create CSV with exact Oracle format directly - ALL columns
                    csv_content = []
                    
                    for _, row in df.iterrows():
                        # Format dates to Oracle format (handle NaT/NaN values)
                        def format_date(date_val):
                            if pd.isna(date_val):
                                return ''
                            try:
                                return pd.to_datetime(date_val).strftime('%Y/%m/%d')
                            except:
                                return str(date_val) if date_val else ''
                        
                        # Helper function to safely get column value  
                        def get_col_value(col_name, default=''):
                            if col_name in df.columns and pd.notna(row[col_name]):
                                val = row[col_name]
                                # Convert float to int if it's a whole number (for IDs)
                                if isinstance(val, float) and val.is_integer():
                                    return str(int(val))
                                return str(val)
                            return default
                        
                        # Create row with ALL columns (all 149 columns)
                        oracle_row = []
                        
                        # Process each column position (0 to 148 for all 149 columns)
                        for i in range(len(df.columns)):
                            col_name = df.columns[i]
                            
                            if i < len(row) and pd.notna(row.iloc[i]):
                                val = row.iloc[i]
                                
                                # Special handling for date columns
                                if 'Date' in col_name or 'DATE' in col_name:
                                    oracle_row.append(format_date(val))
                                # Special handling for amount columns  
                                elif 'Amount' in col_name or 'AMOUNT' in col_name:
                                    if isinstance(val, (int, float)) and val != 0:
                                        oracle_row.append(f"{float(val):.2f}")
                                    else:
                                        oracle_row.append('')
                                # Handle numeric IDs
                                elif isinstance(val, float) and val.is_integer():
                                    oracle_row.append(str(int(val)))
                                # Handle regular values
                                else:
                                    oracle_row.append(str(val))
                            else:
                                oracle_row.append('')
                        
                        # Ensure we have exactly the same number of columns as headers
                        while len(oracle_row) < len(df.columns):
                            oracle_row.append('')
                        
                        # Truncate if somehow longer
                        oracle_row = oracle_row[:len(df.columns)]
                        
                        # Join with commas and add to content
                        csv_content.append(','.join(oracle_row))
                    
                    # Write directly to CSV file with proper comma separation
                    if 'GL_INTERFACE' in sheet_name:
                        csv_filename = zip_dir / 'GL_INTERFACE.csv'
                    else:  # XCC_BUDGET_INTERFACE
                        csv_filename = zip_dir / 'XccBudgetInterface.csv'
                    
                    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                        for line in csv_content:
                            f.write(line + '\n')
                    
                    temp_csv_files.append(str(csv_filename))
                    print(f"Created CSV: {csv_filename} ({len(df)} rows, {len(df.columns)} columns)")
                    continue  # Skip the normal CSV creation
                
                # Clean the sheet name for filename - use proper FBDI naming
                if 'GL_INTERFACE' in sheet_name:
                    # Try Oracle standard GL interface naming
                    csv_filename = zip_dir / "GlInterface.csv"  
                elif 'XCC_BUDGET_INTERFACE' in sheet_name:
                    # Use Oracle standard XCC Budget Interface naming (camelCase without underscores)
                    csv_filename = zip_dir / "XccBudgetInterface.csv"
                else:
                    clean_name = sheet_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                    csv_filename = zip_dir / f"{clean_name}.csv"
                
                # Save CSV in the same directory as the ZIP file
                df.to_csv(csv_filename, index=False, header=False)
                temp_csv_files.append(str(csv_filename))
                print(f"Created CSV: {csv_filename} ({len(df)} rows)")
                
            except Exception as e:
                print(f"Warning: Could not process sheet '{sheet_name}': {e}")
                continue
        
        if not temp_csv_files:
            raise ValueError("No valid data sheets found in Excel file")
        
        # Use PowerShell to create the ZIP file
        files_list = ','.join([f'"{f}"' for f in temp_csv_files])
        
        # Remove existing zip file if it exists and is not locked
        zip_file_path = Path(zip_path)
        if zip_file_path.exists():
            try:
                zip_file_path.unlink()
            except:
                pass  # If we can't delete, PowerShell will handle it
        
        ps_command = f'Compress-Archive -Path {files_list} -DestinationPath "{zip_path}"'
        result = subprocess.run(["powershell", "-Command", ps_command], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("ZIP created using PowerShell")
        else:
            # If PowerShell fails, just continue - the important thing is the CSV was created
            print(f"PowerShell had issues but continuing: {result.stderr}")
            # Try to create with a different name
            alt_zip_path = zip_path.replace('.zip', '_alt.zip')
            ps_command2 = f'Compress-Archive -Path {files_list} -DestinationPath "{alt_zip_path}" -Force'
            result2 = subprocess.run(["powershell", "-Command", ps_command2], 
                                   capture_output=True, text=True)
            if result2.returncode == 0:
                print(f"ZIP created with alternative name: {alt_zip_path}")
                # Copy alternative zip to original name
                try:
                    import shutil
                    shutil.copy2(alt_zip_path, zip_path)
                    print(f"ZIP created: {zip_path}")
                except:
                    print(f"Could not copy to original name, using: {alt_zip_path}")
                    zip_path = alt_zip_path
            else:
                print(f"Alternative ZIP creation also failed: {result2.stderr}")
                # Try with Python zipfile as last resort
                try:
                    import zipfile
                    with zipfile.ZipFile(zip_path, 'w') as zf:
                        for csv_file in temp_csv_files:
                            if os.path.exists(csv_file):
                                # Add file with just its name (not full path) to the ZIP
                                zf.write(csv_file, arcname=Path(csv_file).name)
                    print(f"ZIP created with Python zipfile: {zip_path}")
                except Exception as e:
                    print(f"Python zipfile also failed: {e}")
                    raise RuntimeError("Failed to create ZIP file")
    
    except Exception as e:
        print(f"Error during processing: {e}")
        raise
    finally:
        # CSV files are now saved in the same directory as the ZIP file
        print(f"CSV files saved in directory: {zip_dir}")
        print(f"CSV files created: {[Path(f).name for f in temp_csv_files]}")
    
    return zip_path

def zip_folder(src_path: str, zip_path: str):
    src = Path(src_path)
    
    # Handle both files and directories
    if not src.exists():
        raise FileNotFoundError(f"Path not found: {src_path}")
    
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if src.is_file():
            # Check if it's an Excel file
            if src.suffix.lower() in ['.xlsx', '.xlsm', '.xls']:
                print("Detected Excel file, converting to CSV...")
                # Use temporary approach for Excel files
                return excel_to_csv_and_zip(str(src), zip_path)
            else:
                # If it's a single non-Excel file, add it to the zip
                zf.write(src, arcname=src.name)
        elif src.is_dir():
            # If it's a directory, add all files recursively
            for p in src.rglob("*"):
                if p.is_file():
                    # include all files produced by the FBDI template; most are CSVs
                    zf.write(p, arcname=p.relative_to(src))
        else:
            raise ValueError(f"Path is neither a file nor a directory: {src_path}")
    
    return zip_path

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Zip FBDI output folder/file into a JournalImport_*.zip")
    ap.add_argument("--src", required=True, help="Folder with FBDI CSVs or Excel template file")
    ap.add_argument("--out", help="Zip filename (optional)")
    ap.add_argument("--upload", action="store_true", help="Automatically upload to Oracle Fusion after creating ZIP")
    args = ap.parse_args()

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = args.out or f"JournalImport_{ts}.zip"
    path = str(Path(out).resolve())
    
    try:
        zip_folder(args.src, path)
        print("ZIP created:", path)
        
        # Auto-upload if requested
        if args.upload:
            print("\nAuto-uploading to Oracle Fusion...")
            upload_script = "upload_soap_fbdi.py"
            if os.path.exists(upload_script):
                import subprocess
                upload_cmd = [
                    "python", upload_script,
                    "--csv", path
                ]
                result = subprocess.run(upload_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("Upload completed successfully!")
                    print(result.stdout)
                else:
                    print("Upload failed:")
                    print(result.stderr)
            else:
                print(f"Upload script not found: {upload_script}")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)