from pathlib import Path
from django.conf import settings
from test_upload_fbdi.budget_template_manager import (
    create_sample_budget_data,
    create_budget_from_scratch,
)
from test_upload_fbdi.upload_budget_fbdi import (
    upload_budget_fbdi_to_oracle,
    upload_budget_from_zip,
)
from test_upload_fbdi.budget_import_flow import run_budget_import_flow

def submit_budget_and_upload(transfers, transaction_id,):
    """
    Submit budget transfer data and upload to Oracle Fusion via FBDI.
    
    Args:
        transfers: List of transfer objects with cost_center_code, account_code, project_code attributes
        transaction_id: Transaction ID for the budget transfer
        type: Type of submission (default: "submit")
    
    Returns:
        Tuple: (upload_result, file_path)
            - upload_result: Dictionary with success status and details
            - file_path: Path to the created file (ZIP)
    """
    
    base_dir = Path(settings.BASE_DIR)

    template_path = (
        base_dir / "test_upload_fbdi" / "BudgetImportTemplate.xlsm"
    )
    output_name = base_dir / "test_upload_fbdi" / "XccBudgetInterface"

    print(f"Template path: {template_path}")
    print(f"Output name: {output_name}")

    # Generate budget entry using the transfers
    data = create_sample_budget_data(transfers, transaction_id)

    result = create_budget_from_scratch(
        template_path=str(template_path),
        budget_data=data,
        output_name=str(output_name),
        auto_zip=True,
    )

    print(f"\nCompleted! Final file: {result}")

    # Upload ZIP file directly to Oracle Fusion
    csv_upload_result = None
    if result and result.endswith(".zip"):
        print(f"Uploading ZIP to Oracle Fusion: {result}")
        
        # Use the budget-specific upload function
        group_id = f"BUDGET_{transaction_id}"
        csv_upload_result = run_budget_import_flow(result, transaction_id)

        if csv_upload_result.get("success"):
            print(
                f"FBDI Budget Upload successful! Request ID: {csv_upload_result.get('request_id')}"
            )
            print(
                f"Group ID: {csv_upload_result.get('group_id')}"
            )
        else:
            print(
                f"FBDI Budget Upload failed: {csv_upload_result.get('error')}"
            )
    else:
        print("Budget creation did not produce expected ZIP file")
        csv_upload_result = {
            "success": False,
            "error": "No ZIP file created",
        }
        
    return csv_upload_result, result


def submit_budget_csv_and_upload(transfers, transaction_id, type="submit"):
    """
    Alternative method: Submit budget and upload CSV directly (similar to journal workflow).
    
    Args:
        transfers: List of transfer objects
        transaction_id: Transaction ID for the budget transfer
        type: Type of submission (default: "submit")
    
    Returns:
        Tuple: (upload_result, file_path)
    """
    
    base_dir = Path(settings.BASE_DIR)

    template_path = (
        base_dir / "test_upload_fbdi" / "BudgetImportTemplate.xlsm"
    )
    output_name = base_dir / "test_upload_fbdi" / "SampleBudget"

    print(f"Template path: {template_path}")
    print(f"Output name: {output_name}")

    # Generate budget entry using the transfers
    data = create_sample_budget_data(transfers, transaction_id)
    result = create_budget_from_scratch(
        template_path=str(template_path),
        budget_data=data,
        output_name=str(output_name),
        auto_zip=True,
    )
    print(f"\nCompleted! Final file: {result}")

    # Extract CSV file path and upload to Oracle Fusion (similar to journal workflow)
    csv_upload_result = None
    if result and result.endswith(".zip"):
        # The CSV file should be in the same directory as the ZIP file
        zip_path = Path(result)
        csv_path = zip_path.parent / "XccBudgetInterface.csv"

        if csv_path.exists():
            print(f"Uploading CSV to Oracle Fusion: {csv_path}")
            group_id = f"BUDGET_{transaction_id}_{type.upper()}"
            csv_upload_result = upload_budget_fbdi_to_oracle(str(csv_path), group_id)

            if csv_upload_result.get("success"):
                print(
                    f"FBDI Budget Upload successful! Request ID: {csv_upload_result.get('request_id')}"
                )
                print(
                    f"Group ID: {csv_upload_result.get('group_id')}"
                )
            else:
                print(
                    f"FBDI Budget Upload failed: {csv_upload_result.get('error')}"
                )
        else:
            print(f"CSV file not found at expected location: {csv_path}")
            csv_upload_result = {
                "success": False,
                "error": "CSV file not found",
            }
    else:
        print("Budget creation did not produce expected ZIP file")
        csv_upload_result = {
            "success": False,
            "error": "No ZIP file created",
        }
        
    return csv_upload_result, result