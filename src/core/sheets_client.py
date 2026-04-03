"""
Google Sheets API helper functions.
All functions here assume they are passed an authenticated service object.
"""
import logging
from googleapiclient.errors import HttpError

log = logging.getLogger(__name__)


def column_letter_to_index(col_letter: str) -> int:
    """
    Converts a column letter (A, B, AA, etc.) to a 0-based index.
    
    Examples:
        A -> 0
        B -> 1
        Z -> 25
        AA -> 26
        AZ -> 51
    """
    index = 0
    for char in col_letter:
        index = index * 26 + (ord(char.upper()) - ord('A') + 1)
    return index - 1


def find_event_row(service, sheet_id: str, event_name: str, config: dict) -> int | None:
    """
    Finds the row number for a given event name.
    
    Now more flexible: Returns the row even if it's already filled
    (caller can decide what to do with it).
    
    Returns:
        int: The row number (e.g., 24) if the event is found.
        None: If the event is not found.
    """
    try:
        if not config:
            raise ValueError("Config is None")
        
        sheet_config = config.get('activity_sheet', {})
        if not sheet_config:
            raise ValueError("activity_sheet not found in config")
            
        sheet_name = sheet_config.get('sheet_name')
        name_col = sheet_config.get('event_name_column')
        start_row = sheet_config.get('data_start_row')
        
        if not all([sheet_name, name_col, start_row]):
            raise ValueError("Missing required config values")
        
        # Read just the event name column from start_row onwards
        # e.g., "2025-2026!B8:B"
        range_to_read = f"{sheet_name}!{name_col}{start_row}:{name_col}"
        
        log.info(f"Reading event names from range: {range_to_read}")
        
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_to_read
        ).execute()
        
        values = result.get('values', [])
        if not values:
            log.warning("No data found in the event name column.")
            return None
        
        # Normalize the search term
        normalized_search = event_name.lower().replace(" ", "").replace("_", "")
        
        for i, row in enumerate(values):
            if not row:  # Skip empty rows
                continue
                
            # Normalize the cell value
            cell_value = row[0]
            normalized_cell = cell_value.lower().replace(" ", "").replace("_", "")
            
            # Fuzzy match: does the search term appear in the cell?
            if normalized_search in normalized_cell or normalized_cell in normalized_search:
                actual_row_index = start_row + i
                log.info(f"Found '{event_name}' → matched '{cell_value}' at row {actual_row_index}")
                return actual_row_index
        
        log.error(f"Event '{event_name}' not found in the summary sheet.")
        log.info(f"Available events: {[row[0] if row else '' for row in values[:10]]}")
        return None

    except HttpError as e:
        log.error(f"HTTP Error reading summary sheet: {e}")
        return None
    except Exception as e:
        log.error(f"Error in find_event_row: {e}", exc_info=True)
        return None


def get_participant_count(service, spreadsheet_id: str) -> int | None:
    """
    Gets the participant count from a feedback sheet.
    Assumes count is (total rows - 1) in the *first* tab.
    """
    try:
        sheet_metadata = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="sheets(properties/gridProperties/rowCount)"
        ).execute()
        
        first_sheet_props = sheet_metadata.get("sheets", [{}])[0].get("properties", {})
        row_count = first_sheet_props.get("gridProperties", {}).get("rowCount", 0)
        
        if row_count > 0:
            participant_count = row_count - 1  # Subtract header row
            log.info(f"Extracted Participant Count: {participant_count}")
            return participant_count
        else:
            log.warning("Feedback sheet found, but row count is 0.")
            return None
            
    except HttpError as e:
        log.error(f"Error reading feedback sheet {spreadsheet_id}: {e}")
        return None


def update_event_row(service, sheet_id: str, row_index: int, data: dict, config: dict) -> bool:
    """
    Updates a specific row in the sheet with extracted data.
    
    NEW APPROACH: Instead of building a full row, we update each cell individually.
    This is more reliable and handles multi-letter columns correctly.
    """
    try:
        if not config:
            raise ValueError("Config is None")
            
        sheet_config = config.get('activity_sheet', {})
        if not sheet_config:
            raise ValueError("activity_sheet not found in config")
            
        sheet_name = sheet_config.get('sheet_name')
        column_map = sheet_config.get('column_map')
        
        if not sheet_name or not column_map:
            raise ValueError("Missing required config values")
        
        log.info(f"Updating row {row_index} with {len(data)} data points...")
        
        # Build a list of updates (one per cell)
        updates = []
        
        for field_name, col_letter in column_map.items():
            if field_name in data and data[field_name]:
                # Create a range for this specific cell
                cell_range = f"{sheet_name}!{col_letter}{row_index}"
                value = str(data[field_name])  # Convert to string
                
                updates.append({
                    'range': cell_range,
                    'values': [[value]]
                })
                
                log.debug(f"  {field_name} → {col_letter}{row_index} = {value[:50]}")
        
        if not updates:
            log.warning("No data to update!")
            return False
        
        # Batch update all cells at once
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': updates
        }
        
        result = service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body=body
        ).execute()
        
        updated_cells = result.get('totalUpdatedCells', 0)
        log.info(f"✅ Successfully updated {updated_cells} cells in row {row_index}")
        return True
    
    except HttpError as e:
        log.error(f"HTTP Error writing to sheet: {e}")
        log.error(f"Response: {e.content if hasattr(e, 'content') else 'No content'}")
        return False
    except Exception as e:
        log.error(f"Error in update_event_row: {e}", exc_info=True)
        return False