"""
Drive API Client Module
-----------------------
Combined from old drive_api and drive_client modules.
Provides dumb, atomic wrappers around the Google Drive API.
It handles raw API interactions but contains no business logic.
"""

import logging
import io
import docx
from typing import Optional, Dict, Any, List
from googleapiclient.errors import HttpError
from googleapiclient.discovery import Resource
from googleapiclient.http import MediaIoBaseDownload

log = logging.getLogger(__name__)

SHARED_DRIVE_NAME = "IEDC & IIC Documentation"

def _build_files_list_kwargs(query: str, fields: str, drive_id: Optional[str]) -> dict:
    """
    Build robust files().list kwargs for both Shared Drive and non-Shared Drive parents.
    """
    kwargs = {
        "q": query,
        "fields": fields,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
    }
    if drive_id:
        kwargs["corpora"] = "drive"
        kwargs["driveId"] = drive_id
    else:
        kwargs["corpora"] = "allDrives"
    return kwargs

def get_shared_drive_id(service: Resource, drive_name: str) -> Optional[str]:
    """Resolves a Shared Drive ID by name."""
    log.info(f"🔎 Searching for Shared Drive: '{drive_name}'")
    try:
        response = service.drives().list().execute()
        drives = response.get("drives", [])
        log.info(f"📡 API Response: Found {len(drives)} Shared Drives.")
        
        for drive in drives:
            if drive["name"] == drive_name:
                log.info(f"✅ MATCH FOUND: '{drive_name}' -> {drive['id']}")
                return drive["id"]
        
        log.warning(f"⚠️ Shared Drive '{drive_name}' NOT FOUND in the list.")
        return None
    except Exception as e:
        log.error(f"❌ Error resolving Shared Drive ID: {e}", exc_info=True)
        return None

def find_folder_id(service: Resource, folder_name: str, parent_id: str, shared_drive_id: Optional[str] = None) -> Optional[str]:
    """Finds a folder's Drive ID by its name within a specific parent directory."""
    query = (
        f"mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents "
        f"and trashed=false"
    )
    try:
        list_kwargs = _build_files_list_kwargs(query, "files(id, name)", shared_drive_id)
        results = service.files().list(**list_kwargs).execute()
        items = results.get('files', [])

        for item in items:
            normalized_search = folder_name.lower().replace(" ", "").replace("_", "")
            normalized_item = item['name'].lower().replace(" ", "").replace("_", "")
            if normalized_search in normalized_item:
                return item['id']

        return None
    except HttpError as e:
        log.error(f"HTTP Error finding folder '{folder_name}': {e.reason}")
        return None

def create_folder(service: Resource, name: str, parent_id: str, shared_drive_id: Optional[str] = None) -> Optional[str]:
    """Creates a new folder in Google Drive."""
    folder_meta = {
        'name': name,
        'parents': [parent_id],
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    try:
        kwargs: Dict[str, Any] = {
            "body": folder_meta,
            "fields": "id",
            "supportsAllDrives": True
        }
        folder = service.files().create(**kwargs).execute()
        return folder.get('id')
    except HttpError as e:
        log.error(f"HTTP Error creating folder '{name}': {e.reason}")
        return None

def list_folder_contents(service: Resource, folder_id: str) -> list:
    """Lists all non-folder files inside a folder."""
    query = (
        f"'{folder_id}' in parents "
        f"and mimeType!='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    try:
        list_kwargs = _build_files_list_kwargs(
            query,
            "files(id, name, mimeType, modifiedTime)",
            None
        )
        results = service.files().list(**list_kwargs).execute()
        return results.get('files', [])
    except HttpError as e:
        log.error(f"HTTP Error listing files in folder '{folder_id}': {e.reason}")
        return []

def list_files_in_folder(service: Resource, folder_id: str, shared_drive_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists all active files and folders inside a specific parent folder."""
    kwargs: Dict[str, Any] = {
        "q": f"'{folder_id}' in parents and trashed=false",
        "fields": "files(id, name, mimeType)",
        "pageSize": 1000,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
        "corpora": "drive" if shared_drive_id else "allDrives"
    }
    if shared_drive_id:
        kwargs["driveId"] = shared_drive_id

    try:
        results = service.files().list(**kwargs).execute()
        return results.get('files', [])
    except HttpError as e:
        log.error(f"HTTP Error listing files in {folder_id}: {e.reason}")
        return []

def get_file_content(service: Resource, file_id: str, mime_type: str) -> Optional[str]:
    """Downloads and extracts plain text content from a Google Doc or .docx file."""
    try:
        if mime_type == 'application/vnd.google-apps.document':
            request = service.files().export(fileId=file_id, mimeType='text/plain', supportsAllDrives=True)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return fh.getvalue().decode('utf-8')
            
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            document = docx.Document(fh)
            return "\n".join([p.text for p in document.paragraphs])
            
        elif mime_type.startswith('text/'):
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return fh.getvalue().decode('utf-8')
            
        return None
    except HttpError as e:
        log.error(f"Error reading file content for {file_id}: {e.reason}")
        return None

def update_folder_color(service: Resource, folder_id: str, color_rgb: str = "#ff7537") -> None:
    """Updates the color of a folder in Google Drive."""
    try:
        service.files().update(
            fileId=folder_id,
            body={'folderColorRgb': color_rgb},
            fields='id',
            supportsAllDrives=True
        ).execute()
    except Exception as e:
        log.warning(f"Could not update folder color for {folder_id}: {e}")

def copy_file(service: Resource, file_id: str, new_name: str, parent_id: str, shared_drive_id: Optional[str] = None) -> None:
    """Copies a file to a new location with a new name."""
    copy_metadata = {'name': new_name, 'parents': [parent_id]}
    try:
        service.files().copy(fileId=file_id, body=copy_metadata, supportsAllDrives=True).execute()
    except HttpError as e:
        log.error(f"Failed to copy file {file_id}: {e.reason}")
        raise

def delete_file(service: Resource, file_id: str) -> None:
    """Deletes a file or folder permanently."""
    try:
        service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
    except Exception as e:
        log.error(f"Failed to delete {file_id}: {e}")
        raise
