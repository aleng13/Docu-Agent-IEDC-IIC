"""
Test script for the summary extraction tool.
Run this to debug the entire flow.
"""
import logging
import sys

# Configure detailed logging (UTF-8 for emoji support on Windows)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('summary_test.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

from src.core.config import load_config
from src.core.drive_auth import get_drive_service, get_sheets_service
from src.core import drive_client as drive_api, sheets_client as sheets_api
from src.tools import summary_extractor

def test_summary_extraction():
    """Test the complete summary extraction flow."""
    print("\n" + "="*70)
    print(" "*20 + "SUMMARY EXTRACTION TEST")
    print("="*70 + "\n")
    
    # Get event name from user
    event_name = input("Enter event name to process (e.g., 'IGO IGO'): ").strip()
    if not event_name:
        print("No event name provided. Exiting.")
        return
    
    print(f"\nProcessing event: {event_name}")
    print("-" * 70)
    
    # Step 1: Load config
    print("\n[1/6] Loading configuration...")
    config = load_config()
    if not config:
        print("FAILED: Could not load config.json")
        return
    
    activity_config = config.get('activity_sheet')
    if not activity_config:
        print("FAILED: 'activity_sheet' not found in config.json")
        return
    
    print(f"SUCCESS: Config loaded")
    print(f"    Sheet ID: {activity_config['sheet_id'][:20]}...")
    print(f"    Sheet Name: {activity_config['sheet_name']}")
    
    # Step 2: Get authenticated services
    print("\n[2/6] Authenticating with Google...")
    drive_service = get_drive_service()
    sheets_service = get_sheets_service()
    print("SUCCESS: Authentication successful")
    
    # Step 3: Find the event row
    print(f"\n[3/6] Finding row for '{event_name}' in master sheet...")
    row_number = sheets_api.find_event_row(
        sheets_service,
        activity_config['sheet_id'],
        event_name,
        config
    )
    
    if not row_number:
        print(f"FAILED: Could not find row for '{event_name}'")
        print("   Check that the event name exists in column B of your sheet")
        return
    
    print(f"SUCCESS: Found event at row {row_number}")
    
    # Step 4: Find the event folder
    print(f"\n[4/6] Finding Drive folder for '{event_name}'...")
    parent_folder_id = config.get('parent_folder_id')
    folder_id = drive_api.find_folder_id(drive_service, event_name, parent_folder_id)
    
    if not folder_id:
        print(f"FAILED: Could not find folder for '{event_name}'")
        return
    
    print(f"SUCCESS: Found folder: {folder_id}")
    
    # Step 5: Extract data
    print(f"\n[5/6] Extracting data from folder...")
    print("    (This may take 10-30 seconds for Gemini to process...)")
    
    extracted_data = summary_extractor.extract_event_details(
        drive_service,
        sheets_service,
        folder_id,
        event_name
    )
    
    if not extracted_data or "Error" in extracted_data.get("Status", ""):
        print(f"FAILED: {extracted_data.get('Status', 'Unknown error')}")
        return
    
    print(f"SUCCESS: Extracted {len(extracted_data)} fields")
    print("\n    Preview of extracted data:")
    for key, value in list(extracted_data.items())[:15]:
        print(f"      - {key}: {str(value)[:50]}")
    
    # Step 6: Update the sheet
    print(f"\n[6/6] Writing data to row {row_number}...")
    success = sheets_api.update_event_row(
        sheets_service,
        activity_config['sheet_id'],
        row_number,
        extracted_data,
        config
    )
    
    if success:
        print("SUCCESS! Data written to sheet")
        print(f"\nView your sheet: https://docs.google.com/spreadsheets/d/{activity_config['sheet_id']}")
    else:
        print("FAILED: Could not write to sheet. Check summary_test.log for details")
    
    print("\n" + "="*70)
    print("Test complete. Check summary_test.log for full details")
    print("="*70 + "\n")


if __name__ == '__main__':
    try:
        test_summary_extraction()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\nUnexpected error: {e}")
        print("Check summary_test.log for full stack trace")
