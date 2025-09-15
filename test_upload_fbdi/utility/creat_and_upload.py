


from pathlib import Path
from django.conf import settings
from test_upload_fbdi.journal_template_manager import (
    create_sample_journal_data,
    create_journal_from_scratch,
)
from test_upload_fbdi.upload_soap_fbdi import (
    b64_csv,
    build_soap_envelope,
    upload_fbdi_to_oracle,
)
from account_and_entitys.utils import get_oracle_report_data


def submint_journal_and_upload(transfers,transaction_id,type="submit"):

    base_dir = Path(settings.BASE_DIR)

    template_path = (
        base_dir / "test_upload_fbdi" / "JournalImportTemplate.xlsm"
    )
    output_name = base_dir / "test_upload_fbdi" / "SampleJournal"

    print(f"Template path: {template_path}")
    print(f"Output name: {output_name}")

    # Generate journal entry using the transfers
    data = create_sample_journal_data(transfers,transaction_id,type)
    result = create_journal_from_scratch(
        template_path=str(template_path),
        journal_data=data,
        output_name=str(output_name),
        auto_zip=True,
    )
    print(f"\nCompleted! Final file: {result}")

    # Extract CSV file path and upload to Oracle Fusion
    csv_upload_result = None
    if result and result.endswith(".zip"):
        # The CSV file should be in the same directory as the ZIP file
        zip_path = Path(result)
        csv_path = zip_path.parent / "GL_INTERFACE.csv"

        if csv_path.exists():
            print(f"Uploading CSV to Oracle Fusion: {csv_path}")
            csv_upload_result = upload_fbdi_to_oracle(str(csv_path))

            if csv_upload_result.get("success"):
                print(
                    f"FBDI Upload successful! Request ID: {csv_upload_result.get('request_id')}"
                )
            else:
                print(
                    f"FBDI Upload failed: {csv_upload_result.get('error')}"
                )
        else:
            print(f"CSV file not found at expected location: {csv_path}")
            csv_upload_result = {
                "success": False,
                "error": "CSV file not found",
            }
    else:
        print("Journal creation did not produce expected ZIP file")
        csv_upload_result = {
            "success": False,
            "error": "No ZIP file created",
        }
    return csv_upload_result ,result