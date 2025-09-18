import argparse, os, time, zipfile, tempfile, subprocess
from pathlib import Path
import pandas as pd

import argparse, os, time, zipfile
from pathlib import Path
import pandas as pd
 
def excel_to_csv_and_zip(excel_path: str, zip_path: str):
    """Convert Excel sheets to CSV files and zip them using Python only"""
    excel_file = Path(excel_path)
 
    if not excel_file.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
 
    if excel_file.suffix.lower() not in ['.xlsx', '.xlsm', '.xls']:
        raise ValueError(f"File is not an Excel file: {excel_path}")
 
    zip_dir = Path(zip_path).parent
    print(f"ZIP will be saved to: {zip_path}")
    print(f"CSV files will be saved to: {zip_dir}")
 
    xl = pd.ExcelFile(excel_path)
    print(f"Found sheets: {xl.sheet_names}")
 
    csv_files = []
 
    for sheet_name in xl.sheet_names:
        if 'instruction' in sheet_name.lower():
            print(f"Skipping instruction sheet: {sheet_name}")
            continue
 
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
 
        # Special handling for GL_INTERFACE / XCC_BUDGET_INTERFACE
        if 'GL_INTERFACE' in sheet_name or 'XCC_BUDGET_INTERFACE' in sheet_name:
            headers = [str(df.iloc[3, i]) if pd.notna(df.iloc[3, i]) else f'Col_{i}' for i in range(len(df.columns))]
            df = df.iloc[4:].copy()
            df.columns = headers[:len(df.columns)]
            df = df.dropna(how='all')  # Remove fully empty rows
 
        else:
            # Detect header row for other sheets
            max_non_null = 0
            header_row = -1
            for i in range(min(10, len(df))):
                non_null_count = df.iloc[i].notna().sum()
                if non_null_count > max_non_null:
                    max_non_null = non_null_count
                    header_row = i
            if header_row >= 0:
                df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
            df = df.dropna(axis=0, how='all').dropna(axis=1, how='all')
 
        if df.empty:
            print(f"Skipping empty sheet: {sheet_name}")
            continue
 
        # Determine CSV filename
        clean_name = sheet_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        if 'GL_INTERFACE' in sheet_name:
            csv_filename = zip_dir / "GL_INTERFACE.csv"
        elif 'XCC_BUDGET_INTERFACE' in sheet_name:
            csv_filename = zip_dir / "XccBudgetInterface.csv"
        else:
            csv_filename = zip_dir / f"{clean_name}.csv"
 
        df.to_csv(csv_filename, index=False, header=False, encoding='utf-8')
        csv_files.append(csv_filename)
        print(f"Created CSV: {csv_filename} ({len(df)} rows, {len(df.columns)} columns)")
 
    if not csv_files:
        raise ValueError("No valid sheets to convert to CSV")
 
    # Create ZIP file with Python zipfile
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for f in csv_files:
            zf.write(f, arcname=f.name)
    print(f"ZIP created with Python zipfile: {zip_path}")
 
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