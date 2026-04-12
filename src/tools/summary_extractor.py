"""
The "brains" of the summary writing tool.
This module coordinates the Drive and Sheets APIs and the Gemini LLM
to extract complex data from event folders.
"""
import logging
import json
import re
from docx import Document
import tempfile
import os

# Import your API modules
from src.core import drive_client as drive_api, sheets_client as sheets_api
from src.tools import summary_prompts as gemini_api

log = logging.getLogger(__name__)


def extract_coordinators_from_text(text: str) -> tuple[list[str], list[str]]:
    """
    Extract coordinator names and contact numbers from organizing committee document.
    
    Optimized for Google Docs TABLE format:
    | Sl.no | Name           | Contact No. |
    | 1.    | Abraham Manoj  | 7012079459  |
    | 2.    | Sebastian Robin| 6282767986  |
    
    Returns:
        tuple: (list_of_names, list_of_contact_numbers)
    """
    names = []
    contacts = []
    
    if not text:
        log.warning("No organizing committee text provided")
        return names, contacts
    
    log.info("Extracting coordinators from table format...")
    log.info(f"Text length: {len(text)} characters")
    
    # Split into lines
    lines = text.split('\n')
    
    # Pattern for 10-digit Indian phone numbers
    phone_pattern = r'\b([6-9]\d{9})\b'
    
    # Track if we've found the header row
    found_header = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip header rows (contains "Name", "Contact", "Sl.no")
        if any(header in line.lower() for header in ['sl.no', 'contact no', 'name', 'phone']):
            found_header = True
            log.info(f"  Skipping header: {line}")
            continue
        
        # Look for phone numbers in this line
        phone_matches = re.findall(phone_pattern, line)
        
        if phone_matches:
            for phone in phone_matches:
                if phone not in contacts:
                    contacts.append(phone)
                    log.info(f"  Found contact: {phone}")
                    
                    # Extract name from the same line
                    # Remove the serial number (e.g., "1.", "2.")
                    name_line = re.sub(r'^\d+\.?\s*', '', line)
                    
                    # Remove the phone number from the line
                    name_line = name_line.replace(phone, '')
                    
                    # Clean up extra spaces, tabs, and special characters
                    name_line = re.sub(r'\s+', ' ', name_line)  # Multiple spaces to single space
                    name_line = re.sub(r'[|\\\/\-]+', ' ', name_line)  # Remove table separators
                    name_line = name_line.strip()
                    
                    # Validate and add name
                    if name_line and len(name_line) > 2 and len(name_line) < 50:
                        # Make sure it's not just numbers or special chars
                        if re.search(r'[a-zA-Z]{2,}', name_line):
                            if name_line not in names:
                                names.append(name_line)
                                log.info(f"  Found name: {name_line}")
    
    # Quality check: If we have more contacts than names, something went wrong
    if len(contacts) > len(names) and contacts:
        log.warning(f"More contacts ({len(contacts)}) than names ({len(names)}). Attempting name recovery...")
        
        # Try to find names in lines without phone numbers
        name_candidates = []
        for line in lines:
            line = line.strip()
            if not line or any(header in line.lower() for header in ['sl.no', 'contact no', 'name']):
                continue
            
            # Skip lines with phone numbers (already processed)
            if re.search(phone_pattern, line):
                continue
            
            # Clean the line
            clean_line = re.sub(r'^\d+\.?\s*', '', line)  # Remove numbering
            clean_line = re.sub(r'[|\\\/\-]+', ' ', clean_line)  # Remove separators
            clean_line = re.sub(r'\s+', ' ', clean_line).strip()
            
            if clean_line and 2 < len(clean_line) < 50 and re.search(r'[a-zA-Z]{2,}', clean_line):
                name_candidates.append(clean_line)
        
        # Add recovered names up to the number of contacts
        for candidate in name_candidates:
            if len(names) >= len(contacts):
                break
            if candidate not in names:
                names.append(candidate)
                log.info(f"  Recovered name: {candidate}")
    
    log.info(f"Extraction complete: {len(names)} names, {len(contacts)} contacts")
    
    # Final validation: ensure same count
    if len(names) != len(contacts):
        log.warning(f"Mismatch: {len(names)} names vs {len(contacts)} contacts")
    
    return names, contacts


def extract_event_details(drive_service, sheets_service, folder_id: str, event_name: str, shared_drive_id: str = None) -> dict:
    """
    Scans files, reads their content, and uses AI to extract data points.
    Returns a dictionary of extracted data mapped to sheet column names.
    """
    import io
    import re
    from docx import Document
    from googleapiclient.http import MediaIoBaseDownload

    def extract_from_docx_bytes(docx_bytes: bytes):
        """
        Parse organizing committee from .docx bytes (table format).
        Returns (names_list, phones_list)
        """
        names = []
        phones = []
        try:
            fh = io.BytesIO(docx_bytes)
            doc = Document(fh)
        except Exception as e:
            log.warning(f"  âš ï¸  Failed to open docx bytes for parsing: {e}")
            return names, phones

        # regexes for phone detection
        phone_extract_re = re.compile(r'(\+?0?\d{10,14})')
        bracket_phone_re = re.compile(r'[\[\(]\s*(\+?0?\d{10,14})\s*[\]\)]')

        for table in doc.tables:
            # build rows as lists of cell texts
            rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
            if len(rows) < 2:
                continue

            # try to detect columns
            headers = [h.lower() for h in rows[0]]
            name_idx = None
            phone_idx = None
            for i, h in enumerate(headers):
                if 'name' in h or 'member' in h or 'candidate' in h:
                    name_idx = i
                if any(k in h for k in ('contact', 'phone', 'mobile', 'contact no', 'mobile no')):
                    phone_idx = i

            # fallback heuristics
            if name_idx is None and phone_idx is None and len(rows[0]) >= 2:
                # common pattern: [Sl.no, Name] or [Sl.no, Name, Contact]
                # if 2 columns, assume name is column 1
                if len(rows[0]) == 2:
                    name_idx = 1
                    phone_idx = None
                else:
                    name_idx = 1
                    phone_idx = len(rows[0]) - 1

            if name_idx is None:
                continue

            # parse rows
            for r in rows[1:]:
                # ensure index safety
                raw_name_cell = r[name_idx] if name_idx < len(r) else ''
                raw_phone_cell = (r[phone_idx] if phone_idx is not None and phone_idx < len(r) else '') if phone_idx is not None else ''

                # try phone from phone column first
                phone_digits = ''
                if raw_phone_cell:
                    phone_digits = re.sub(r'\D', '', raw_phone_cell or '')
                    if len(phone_digits) >= 10:
                        phone_digits = phone_digits[-10:]
                    else:
                        phone_digits = ''

                # if none, try bracketed or inline phone inside name cell
                if not phone_digits and raw_name_cell:
                    m = bracket_phone_re.search(raw_name_cell)
                    if m:
                        phone_digits = re.sub(r'\D', '', m.group(1))[-10:]
                    else:
                        m2 = phone_extract_re.search(raw_name_cell)
                        if m2:
                            phone_digits = re.sub(r'\D', '', m2.group(1))[-10:]

                # clean name: remove bracketed phone, remove bare phone sequences, strip separators
                cleaned_name = raw_name_cell
                cleaned_name = re.sub(r'[\[\(]\s*\+?0?\d{8,14}\s*[\]\)]', '', cleaned_name)
                cleaned_name = re.sub(r'\+?0?\d{8,14}', '', cleaned_name)
                cleaned_name = re.sub(r'[\|\-\/]+', ' ', cleaned_name)
                cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()

                # add if present
                if cleaned_name or phone_digits:
                    if cleaned_name and cleaned_name not in names:
                        names.append(cleaned_name)
                    if phone_digits and phone_digits not in phones:
                        phones.append(phone_digits)

            if names or phones:
                break

        return names, phones

    log.info(f"=" * 60)
    log.info(f"Starting summary extraction for: {event_name}")
    log.info(f"Folder ID: {folder_id}")
    log.info(f"=" * 60)

    # 1. Get ALL subfolders in the event folder
    log.info("Step 1: Finding all subfolders...")
    try:
        query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        drive_id = shared_drive_id
        
        list_kwargs = {
            "q": query,
            "fields": "files(id, name)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }
        if drive_id:
            list_kwargs["corpora"] = "drive"
            list_kwargs["driveId"] = drive_id
        else:
            list_kwargs["corpora"] = "allDrives"
            
        results = drive_service.files().list(**list_kwargs).execute()
        subfolders = results.get('files', [])
        log.info(f"Found {len(subfolders)} subfolders")
        for folder in subfolders:
            log.info(f"  - {folder['name']}")
    except Exception as e:
        log.error(f"Error listing subfolders: {e}")
        subfolders = []

    if not subfolders:
        return {
            "Event Name": event_name,
            "Status": "âŒ No subfolders found",
            "Document folder link": f"https://drive.google.com/drive/folders/{folder_id}"
        }

    # 2. Find key subfolders
    report_folder = None
    feedback_folder = None
    registration_folder = None
    organizing_folder = None

    for folder in subfolders:
        name_lower = folder['name'].lower()
        if 'report' in name_lower:
            report_folder = folder
            log.info(f"  âœ“ Found Report folder: {folder['name']}")
        elif 'feedback' in name_lower:
            feedback_folder = folder
            log.info(f"  âœ“ Found Feedback folder: {folder['name']}")
        elif 'registration' in name_lower:
            registration_folder = folder
            log.info(f"  âœ“ Found Registration folder: {folder['name']}")
        elif 'organizing' in name_lower and 'committee' in name_lower:
            organizing_folder = folder
            log.info(f"  âœ“ Found Organizing Committee folder: {folder['name']}")

    # 3. Read Report
    report_text = ""
    if report_folder:
        log.info(f"Step 2: Reading report...")
        files = drive_api.list_folder_contents(drive_service, report_folder['id'])
        for file in files:
            mime = file.get('mimeType', '')
            if mime in ['application/vnd.google-apps.document',
                       'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                content = drive_api.get_file_content(drive_service, str(file['id']), str(mime))
                if content:
                    report_text = content
                    log.info(f"  âœ… Read {len(report_text)} chars from report")
                break
    else:
        log.warning("  âš ï¸  No Report folder found")

    # 4. Read Organizing Committee and Extract Coordinators
    coordinator_text = ""
    coordinator_names = []
    coordinator_contacts = []

    if organizing_folder:
        log.info(f"Step 3: Reading organizing committee...")
        files = drive_api.list_folder_contents(drive_service, organizing_folder['id'])
        log.info(f"  Found {len(files)} files in organizing committee folder")

        for file in files:
            fid = str(file.get('id'))
            fname = file.get('name')
            fmime = file.get('mimeType', '')
            log.info(f"  Checking file: {fname} (type: {fmime})")

            # Prefer DOCX table parsing for real Word files
            if fmime == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                try:
                    request = drive_service.files().get_media(
                    fileId=fid,
                    supportsAllDrives=True
                )
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                    fh.seek(0)
                    docx_bytes = fh.read()
                    log.info(f"  âœ… Downloaded .docx bytes ({len(docx_bytes)} bytes) for file: {fname}")

                    # Parse the docx bytes to extract table-based names & phones
                    coordinator_names, coordinator_contacts = extract_from_docx_bytes(docx_bytes)
                    log.info(f"  âœ… Extracted {len(coordinator_names)} names and {len(coordinator_contacts)} contacts from DOCX table")
                except Exception as e:
                    log.warning(f"  âš ï¸  Failed to download/parse DOCX: {e}")
                break

            # If it's a Google Doc, fall back to text extraction via drive_api then export to docx
            if fmime == 'application/vnd.google-apps.document':
                try:
                    content = drive_api.get_file_content(drive_service, fid, fmime)
                    if content:
                        coordinator_text = content
                        log.info(f"  âœ… Read {len(coordinator_text)} chars from organizing committee (Google Doc)")
                        log.info(f"  First 200 chars: {coordinator_text[:200]}")
                        txt_names, txt_contacts = extract_coordinators_from_text(coordinator_text)
                        if txt_names or txt_contacts:
                            coordinator_names, coordinator_contacts = txt_names, txt_contacts
                            log.info(f"  âœ… Extracted {len(coordinator_names)} coordinators and {len(coordinator_contacts)} contacts from Google Doc text")
                            break
                except Exception as e:
                    log.warning(f"  âš ï¸  Failed to read Google Doc content: {e}")

                # try export-as-docx and parse
                try:
                    export_req = drive_service.files().export_media(
                        fileId=fid,
                        mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        supportsAllDrives=True
                    )
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, export_req)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                    fh.seek(0)
                    exported_bytes = fh.read()
                    log.info(f"  âœ… Exported Google Doc to docx bytes ({len(exported_bytes)} bytes) for {fname}")
                    names, phones = extract_from_docx_bytes(exported_bytes)
                    if names or phones:
                        coordinator_names, coordinator_contacts = names, phones
                        log.info(f"  âœ… Parsed {len(names)} names and {len(phones)} phones from exported Google Doc")
                        break
                except Exception as e:
                    log.debug(f"  Export-as-docx failed: {e}")

            # Other file types/fallback: try get_media and parse as docx
            try:
                request = drive_service.files().get_media(
                    fileId=fid,
                    supportsAllDrives=True
                )
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                fh.seek(0)
                raw_bytes = fh.read()
                if raw_bytes:
                    log.info(f"  Fallback: downloaded {len(raw_bytes)} bytes for {fname}; attempting to parse as docx")
                    names, phones = extract_from_docx_bytes(raw_bytes)
                    if names or phones:
                        coordinator_names, coordinator_contacts = names, phones
                        log.info(f"  âœ… Fallback parse succeeded: {len(names)} names, {len(phones)} phones")
                        break
                    else:
                        log.info("  Fallback parse found no table data")
            except Exception as e:
                log.debug(f"  Fallback download/parse error for {fname}: {e}")

        log.info(f"  Final extraction result: {len(coordinator_names)} names, {len(coordinator_contacts)} contacts")
        log.info(f"  Sample names: {coordinator_names[:5]} | Sample phones: {coordinator_contacts[:5]}")

    else:
        log.warning("  âš ï¸  No Organizing Committee folder found")

    # 5. Get Registration & Feedback counts + responses
    log.info(f"Step 4: Reading registration & feedback...")
    registration_count = None
    feedback_count = None
    feedback_responses = ""

    if registration_folder:
        log.info("  Looking for registration sheet...")
        files = drive_api.list_folder_contents(drive_service, registration_folder['id'])
        for file in files:
            log.info(f"    Checking: {file.get('name')} (type: {file.get('mimeType')})")
            if file.get('mimeType') == 'application/vnd.google-apps.spreadsheet':
                registration_count = sheets_api.get_participant_count(sheets_service, str(file['id']))
                log.info(f"  âœ… Registration count: {registration_count}")
                break
    else:
        log.warning("  âš ï¸  No Registration folder found")

    if feedback_folder:
        log.info("  Looking for feedback sheet...")
        files = drive_api.list_folder_contents(drive_service, feedback_folder['id'])
        for file in files:
            log.info(f"    Checking: {file.get('name')} (type: {file.get('mimeType')})")
            if file.get('mimeType') == 'application/vnd.google-apps.spreadsheet':
                sheet_id = str(file['id'])
                feedback_count = sheets_api.get_participant_count(sheets_service, sheet_id)
                log.info(f"  âœ… Feedback count: {feedback_count}")

                # Read actual responses
                try:
                    data = sheets_service.spreadsheets().values().get(
                        spreadsheetId=sheet_id, range='A1:Z100'
                    ).execute()
                    values = data.get('values', [])
                    if values and len(values) > 1:
                        headers = values[0]
                        responses = values[1:]
                        feedback_responses = f"FEEDBACK ({len(responses)} responses):\n"
                        feedback_responses += f"Headers: {', '.join(headers)}\n\n"
                        for i, row in enumerate(responses[:20], 1):
                            feedback_responses += f"{i}. {' | '.join(str(c) for c in row)}\n"
                        log.info(f"  âœ… Read {len(responses)} feedback entries")
                except Exception as e:
                    log.warning(f"  âš ï¸  Couldn't read feedback responses: {e}")
                break
    else:
        log.warning("  âš ï¸  No Feedback folder found")

    # 6. Build additional data for Gemini
    additional_data = ""
    if coordinator_text:
        additional_data += f"\nORGANIZING COMMITTEE:\n{coordinator_text}\n"
    if feedback_responses:
        additional_data += f"\n{feedback_responses}\n"
    if registration_count:
        additional_data += f"\nREGISTRATIONS: {registration_count}\n"
    if feedback_count:
        additional_data += f"FEEDBACK COUNT: {feedback_count}\n"

    # 7. Call Gemini
    log.info("Step 5: Calling Gemini...")
    json_string = gemini_api.extract_details_from_text(report_text, additional_data)

    try:
        extracted_data = json.loads(json_string)
        if "error" in extracted_data:
            return {
                "Event Name": event_name,
                "Status": f"âŒ {extracted_data['error']}",
                "Document folder link": f"https://drive.google.com/drive/folders/{folder_id}"
            }
    except json.JSONDecodeError:
        log.error(f"Failed to parse Gemini response: {json_string[:200]}")
        return {
            "Event Name": event_name,
            "Status": "âŒ Invalid AI response",
            "Document folder link": f"https://drive.google.com/drive/folders/{folder_id}"
        }

    # 8. Add Coordinator Information (CRITICAL FIX!)
    if coordinator_names:
        # Format as comma-separated string
        extracted_data["Coordinators"] = ", ".join(coordinator_names)
        log.info(f"  âœ… Added Coordinators: {extracted_data['Coordinators']}")
    else:
        extracted_data["Coordinators"] = ""
        log.warning("  âš ï¸  No coordinators extracted")

    if coordinator_contacts:
        # Format as comma-separated string
        extracted_data["Contact Number of Coordinators"] = ", ".join(coordinator_contacts)
        log.info(f"  âœ… Added Contacts: {extracted_data['Contact Number of Coordinators']}")
    else:
        extracted_data["Contact Number of Coordinators"] = ""
        log.warning("  âš ï¸  No contact numbers extracted")

# -----------------------------------------------------------
    # 9. Calculate Participation Percentage (SMART FALLBACK LOGIC)
    # -----------------------------------------------------------
    def to_int(x):
        try:
            if x is None: return None
            if isinstance(x, (int, float)): return int(x)
            x = str(x).strip()
            if ":" in x: return None # Time string
            digits = re.sub(r'\D', '', x)
            return int(digits) if digits else None
        except: return None

    try:
        # A. Actual Participants (The Numerator)
        # Priority: AI Report -> Attendance Sheet -> Feedback Sheet
        actual_participants = to_int(extracted_data.get("No. of Participants"))

        if actual_participants is None:
             # Check Attendance Folder
             attendance_folder = next((sf for sf in subfolders if "attendance" in sf["name"].lower()), None)
             if attendance_folder:
                 att_files = drive_api.list_folder_contents(drive_service, attendance_folder["id"])
                 for af in att_files:
                     if af.get("mimeType") == "application/vnd.google-apps.spreadsheet":
                         att_count = sheets_api.get_participant_count(sheets_service, str(af['id']))
                         if to_int(att_count):
                             actual_participants = to_int(att_count)
                             log.info(f"  Using Attendance Sheet count ({actual_participants}) as actuals.")
                             break
        
        if actual_participants is None:
            # Check Feedback Folder
            actual_participants = to_int(feedback_count)
            if actual_participants:
                log.info(f"  Using Feedback count ({actual_participants}) as actuals.")

        # B. Total Registered (The Denominator)
        total_registered = to_int(registration_count)

        # C. Calculate Percentage
        if total_registered and total_registered > 0:
            # Scenario 1: We have a valid Registration Sheet
            numerator = actual_participants if actual_participants else 0
            pct = round((numerator / total_registered) * 100, 1)
            extracted_data["Percentage Participation"] = f"{pct}%"
            log.info(f"  âœ… Participation: {pct}% ({numerator} attended / {total_registered} registered)")

        elif actual_participants and actual_participants > 0:
            # Scenario 2: No Registration Sheet (Walk-in event) -> Assume 100%
            extracted_data["Percentage Participation"] = "100%"
            log.info(f"  âš ï¸  No Reg Sheet. Defaulting to 100% (Walk-in assumption).")
            
            # If AI missed the count, backfill it now so the sheet isn't empty
            if not extracted_data.get("No. of Participants"):
                extracted_data["No. of Participants"] = actual_participants

        else:
            # Scenario 3: No data at all
            extracted_data["Percentage Participation"] = ""
            log.warning("  âš ï¸  Cannot calculate %: No data sources found.")

        # Final check: Ensure 'No. of Participants' is filled if we found a number anywhere
        if not extracted_data.get("No. of Participants") and actual_participants:
            extracted_data["No. of Participants"] = actual_participants

    except Exception as e:
        log.exception(f"Error calculating participation: {e}")
        extracted_data["Percentage Participation"] = ""

    # 11. Add final fields
    extracted_data["Event Name"] = event_name
    extracted_data["Filled By"] = "DocuAgent"
    extracted_data["Document folder link"] = f"https://drive.google.com/drive/folders/{folder_id}"

    log.info("=" * 60)
    log.info("FINAL EXTRACTED DATA:")
    for k, v in extracted_data.items():
        if v:
            display_value = str(v)[:100] if len(str(v)) > 100 else str(v)
            log.info(f"  {k}: {display_value}")
        else:
            log.warning(f"  {k}: [EMPTY]")
    log.info("=" * 60)

    return extracted_data
