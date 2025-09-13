# Journal Template Manager - Oracle FBDI Journal Import Helper

This module provides easy-to-use functions for managing Oracle Fusion FBDI (File-Based Data Import) Journal Import Templates. It allows you to create clean templates, fill them with data, and generate ZIP files ready for Oracle Fusion import.

## 📋 Overview

The Journal Template Manager solves the problem of working with Oracle FBDI templates by:

1. **Creating clean templates** - Makes a copy of your template with empty data rows
2. **Filling with new data** - Populates the template with your journal entry data
3. **Generating FBDI-ready files** - Creates ZIP files that can be directly imported into Oracle Fusion
4. **Data validation** - Ensures your data meets Oracle requirements before processing

## 🔧 Key Components

### Files Structure
```
├── JournalImportTemplate.xlsm          # Original Oracle FBDI template
├── journal_template_manager.py         # Core template management functions
├── journal_helper.py                   # User-friendly helper functions  
├── demo_journal_manager.py             # Examples and demonstrations
├── zip_fbdi.py                         # Existing ZIP creation functionality
└── README_Journal_Manager.md           # This documentation
```

### Required Columns
The following columns are **mandatory** for all journal entries:
- Status Code
- Ledger ID
- Effective Date of Transaction
- Journal Source
- Journal Category
- Currency Code
- Journal Entry Creation Date
- Actual Flag

## 🚀 Quick Start

### Basic Usage

```python
from journal_helper import create_journal_from_data

# Your journal data as list of dictionaries
journal_data = [
    {
        "Status Code": "NEW",
        "Ledger ID": "300000205309206", 
        "Effective Date of Transaction": "2025-09-13",
        "Journal Source": "Balance Transfer",
        "Journal Category": "Adjustment",
        "Currency Code": "AED",
        "Journal Entry Creation Date": "2025-09-13",
        "Actual Flag": "E",
        "Segment1": "10172",
        "Segment2": "C070003", 
        "Entered Debit Amount": 1000.00,
        "REFERENCE4 (Journal Entry Name)": "My Journal Entry",
        "REFERENCE5 (Journal Entry Description)": "Sample journal entry"
    },
    # Add more entries...
]

# Create journal file (automatically creates ZIP)
result_path = create_journal_from_data(
    journal_data=journal_data,
    output_name="MyJournal",
    create_zip=True
)

print(f"Created: {result_path}")  # Output: MyJournal.zip
```

### Creating Balanced Journal Entries

```python
from journal_helper import create_balanced_journal_entry, create_journal_from_data

# Create a balanced journal entry
journal_lines = create_balanced_journal_entry(
    entry_name="Asset Transfer",
    entry_description="Transfer equipment between departments",
    ledger_id="300000205309206",
    effective_date="2025-09-13",
    debit_entries=[
        {"account": "10172", "cost_center": "C070003", "amount": 5000.00, "description": "Equipment received"}
    ],
    credit_entries=[
        {"account": "10001", "cost_center": "C070001", "amount": 5000.00, "description": "Equipment transferred"}
    ]
)

# Create the journal file
result = create_journal_from_data(journal_lines, output_name="AssetTransfer", create_zip=True)
```

### Data Validation

```python
from journal_helper import validate_journal_data

# Validate your data before processing
is_valid, errors = validate_journal_data(journal_data)

if not is_valid:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Data is valid!")
```

## 🔍 Main Functions

### `create_journal_from_data()`
Main function for creating journal files from data.

**Parameters:**
- `journal_data`: List of dictionaries containing journal entry data
- `template_path`: Path to JournalImportTemplate.xlsm (default: "JournalImportTemplate.xlsm")  
- `output_name`: Name for output files (auto-generated if not provided)
- `validate_data`: Whether to validate data before processing (default: True)
- `create_zip`: Whether to create ZIP file for FBDI import (default: True)

**Returns:** Path to created file (Excel or ZIP)

### `create_balanced_journal_entry()`
Helper function to create balanced journal entries.

**Parameters:**
- `entry_name`: Name for the journal entry
- `entry_description`: Description for the journal entry  
- `ledger_id`: Oracle Ledger ID
- `effective_date`: Effective date (YYYY-MM-DD format)
- `debit_entries`: List of debit line items
- `credit_entries`: List of credit line items

**Returns:** List of journal entry dictionaries

### `validate_journal_data()`
Validates journal data to ensure all required fields are present.

**Parameters:**
- `journal_data`: List of journal entry dictionaries

**Returns:** Tuple of (is_valid, list_of_errors)

## 📊 Data Format

Each journal entry should be a dictionary with the following structure:

```python
{
    # Required fields
    "Status Code": "NEW",
    "Ledger ID": "300000205309206",
    "Effective Date of Transaction": "2025-09-13", 
    "Journal Source": "Balance Transfer",
    "Journal Category": "Adjustment",
    "Currency Code": "AED",
    "Journal Entry Creation Date": "2025-09-13",
    "Actual Flag": "E",
    
    # Chart of Accounts segments
    "Segment1": "10172",           # Account
    "Segment2": "C070003",         # Cost Center
    "Segment3": "",                # Additional segments as needed
    
    # Amounts (use either debit OR credit, not both)
    "Entered Debit Amount": 1000.00,
    "Entered Credit Amount": "",
    
    # Reference fields
    "REFERENCE4 (Journal Entry Name)": "My Journal Entry",
    "REFERENCE5 (Journal Entry Description)": "Description of the entry",
    "REFERENCE10 (Journal Entry Line Description)": "Line description",
    
    # Additional optional fields...
}
```

## 🎯 Examples

### Example 1: Simple Journal Entry

```python
from journal_helper import create_journal_from_data

# Simple debit/credit journal
data = [
    {
        "Status Code": "NEW",
        "Ledger ID": "300000205309206", 
        "Effective Date of Transaction": "2025-09-13",
        "Journal Source": "Manual",
        "Journal Category": "Adjustment", 
        "Currency Code": "AED",
        "Journal Entry Creation Date": "2025-09-13",
        "Actual Flag": "E",
        "Segment1": "50001",  # Expense account
        "Entered Debit Amount": 2500.00,
        "REFERENCE4 (Journal Entry Name)": "Office Supplies",
        "REFERENCE10 (Journal Entry Line Description)": "Debit - Office supplies expense"
    },
    {
        "Status Code": "NEW",
        "Ledger ID": "300000205309206",
        "Effective Date of Transaction": "2025-09-13", 
        "Journal Source": "Manual",
        "Journal Category": "Adjustment",
        "Currency Code": "AED",
        "Journal Entry Creation Date": "2025-09-13",
        "Actual Flag": "E",
        "Segment1": "10001",  # Cash account
        "Entered Credit Amount": 2500.00,
        "REFERENCE4 (Journal Entry Name)": "Office Supplies", 
        "REFERENCE10 (Journal Entry Line Description)": "Credit - Cash payment"
    }
]

result = create_journal_from_data(data, output_name="OfficeSupplies")
```

### Example 2: Month-End Accrual

```python
from journal_helper import create_balanced_journal_entry, create_journal_from_data

# Create month-end accrual
accrual = create_balanced_journal_entry(
    entry_name="Month-End Accrual - September 2025",
    entry_description="Accrual of monthly operating expenses",
    ledger_id="300000205309206",
    effective_date="2025-09-30",
    journal_source="Month End",
    journal_category="Accrual",
    debit_entries=[
        {"account": "60001", "cost_center": "C070001", "amount": 8000.00, "description": "Rent expense"},
        {"account": "60002", "cost_center": "C070001", "amount": 1500.00, "description": "Utilities expense"},
        {"account": "60003", "cost_center": "C070002", "amount": 3000.00, "description": "Professional services"}
    ],
    credit_entries=[
        {"account": "20010", "cost_center": "0000000", "amount": 12500.00, "description": "Accrued expenses"}
    ]
)

result = create_journal_from_data(accrual, output_name="MonthEnd_Accrual_202509")
```

## 🛠 Advanced Usage

### Working with CSV Data

```python
from journal_helper import create_journal_from_csv

# Create journal from CSV file
result = create_journal_from_csv(
    csv_path="journal_data.csv",
    output_name="ImportedJournal",
    create_zip=True
)
```

### Custom Template Path

```python
# Use custom template file
result = create_journal_from_data(
    journal_data=my_data,
    template_path="/path/to/my/CustomTemplate.xlsm",
    output_name="CustomJournal"
)
```

### Skip Data Validation

```python
# Skip validation (use with caution)
result = create_journal_from_data(
    journal_data=my_data,
    validate_data=False,
    create_zip=True
)
```

## ⚠️ Important Notes

1. **Template File**: Ensure `JournalImportTemplate.xlsm` exists in your working directory
2. **Data Validation**: Always validate data before processing for production use
3. **Balanced Entries**: Ensure debit and credit amounts are balanced for complete journal entries
4. **Date Format**: Use YYYY-MM-DD format for all date fields
5. **Amount Fields**: Use either debit OR credit amount per line, not both
6. **Segment Mapping**: Map your chart of accounts to the correct Segment columns

## 🔧 Troubleshooting

### Common Issues

**"Template file not found"**
- Ensure `JournalImportTemplate.xlsm` is in the current directory
- Check the file path and spelling

**"Data validation failed"**
- Check that all required columns are present
- Verify date format is YYYY-MM-DD
- Ensure amounts are numeric
- Check that lines have either debit OR credit, not both

**"ZIP creation failed"**
- Check file permissions
- Ensure PowerShell is available (Windows)
- Try with `create_zip=False` to get Excel file only

### Getting Help

Run the demo script to see examples:
```bash
python demo_journal_manager.py
```

Check required columns:
```python
from journal_helper import get_required_columns
print(get_required_columns())
```

## 🔄 Workflow Integration

This module integrates with the existing `zip_fbdi.py` and `upload_soap_fbdi.py` workflow:

1. **Create Journal** → Use this module to create journal files
2. **Generate ZIP** → Automatically handled by `create_zip=True`
3. **Upload to Oracle** → Use existing `upload_soap_fbdi.py` with the generated ZIP

Complete workflow example:
```python
# 1. Create journal
result_path = create_journal_from_data(my_data, create_zip=True)

# 2. Upload to Oracle (using existing upload script)
import subprocess
subprocess.run(["python", "upload_soap_fbdi.py", "--csv", result_path])
```

---

## 📝 License

This module is part of the Tanfeez_Backend project and follows the same licensing terms.

## 🤝 Contributing

When contributing to this module, please:
1. Test with the demo script
2. Validate against Oracle FBDI requirements  
3. Update documentation for new features
4. Follow existing code style patterns