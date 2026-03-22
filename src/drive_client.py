"""
Drive API Client Module
-----------------------
Provides dumb, atomic wrappers around the Google Drive API.
It handles raw API interactions but contains no business logic.
"""

import logging
from typing import Optional, Dict, Any, List
from googleapiclient.errors import HttpError
from googleapiclient.discovery import Resource

log = logging.getLogger(__name__)

def find_folder_id(service: Resource, folder_name: str, parent_id: str, shared_drive_id: Optional[str] = None) -> Optional[str]:
    """
    Finds a folder's Drive ID by its name within a specific parent directory.

    Args:
        service (Resource): Authenticated Google Drive service object.
        folder_name (str): The name of the folder to search for.
        parent_id (str): The Drive ID of the parent folder.
        shared_drive_id (Optional[str]): The ID of the Shared Drive to search within, if applicable. Defaults to None.

    Returns:
        Optional[str]: The Drive ID of the folder if found, otherwise None.
    """
    query = (
        f"mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents "
        f"and trashed=false"
    )
    
    kwargs: Dict[str, Any] = {
        "q": query,
        "fields": "files(id, name)",
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
        "corpora": "drive" if shared_drive_id else "user"
    }
    if shared_drive_id:
        kwargs["driveId"] = shared_drive_id

    try:
        results = service.files().list(**kwargs).execute()
        items = results.get('files', [])

        for item in items:
            normalized_search = folder_name.lower().replace(" ", "").replace("_", "")
            normalized_item = item['name'].lower().replace(" ", "").replace("_", "")
            if normalized_search in normalized_item:
                return item['id']

        return None
    except HttpError as e:
        log.error(f"HTTP Error finding folder '{folder_name}': {e}")
        return None


def create_folder(service: Resource, name: str, parent_id: str, shared_drive_id: Optional[str] = None) -> Optional[str]:
    """
    Creates a new folder in Google Drive.

    Args:
        service (Resource): Authenticated Google Drive service object.
        name (str): The name of the new folder to create.
        parent_id (str): The Drive ID of the parent directory.
        shared_drive_id (Optional[str]): The ID of the Shared Drive, if applicable. Defaults to None.

    Returns:
        Optional[str]: The Drive ID of the newly created folder, or None if creation failed.
    """
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
        log.error(f"HTTP Error creating folder '{name}': {e}")
        return None

def update_folder_color(service: Resource, folder_id: str, color_rgb: str = "#ff7537") -> None:
    """
    Updates the color of a folder in Google Drive.

    Args:
        service (Resource): Authenticated Google Drive service object.
        folder_id (str): The Drive ID of the folder to visually color.
        color_rgb (str): Hex color code formatted string. Defaults to '#ff7537' (Orange).
    """
    try:
        service.files().update(
            fileId=folder_id,
            body={'folderColorRgb': color_rgb},
            fields='id',
            supportsAllDrives=True
        ).execute()
    except Exception as e:
        log.warning(f"Could not update folder color for {folder_id}: {e}")

def list_files_in_folder(service: Resource, folder_id: str, shared_drive_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Lists all active files and folders inside a specific parent folder.

    Args:
        service (Resource): Authenticated Google Drive service object.
        folder_id (str): The Drive ID of the parent folder to scan.
        shared_drive_id (Optional[str]): The ID of the Shared Drive, if applicable. Defaults to None.

    Returns:
        List[Dict[str, Any]]: A list of file dictionaries containing 'id', 'name', and 'mimeType'.
    """
    kwargs: Dict[str, Any] = {
        "q": f"'{folder_id}' in parents and trashed=false",
        "fields": "files(id, name, mimeType)",
        "pageSize": 100,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
        "corpora": "drive" if shared_drive_id else "user"
    }
    if shared_drive_id:
        kwargs["driveId"] = shared_drive_id

    try:
        results = service.files().list(**kwargs).execute()
        return results.get('files', [])
    except HttpError as e:
        log.error(f"HTTP Error listing files in {folder_id}: {e}")
        return []

def copy_file(service: Resource, file_id: str, new_name: str, parent_id: str, shared_drive_id: Optional[str] = None) -> None:
    """
    Copies a file to a new location with a new name.

    Args:
        service (Resource): Authenticated Google Drive service object.
        file_id (str): The Drive ID of the source file to copy.
        new_name (str): The new name for the copied file.
        parent_id (str): The Drive ID of the destination parent folder.
        shared_drive_id (Optional[str]): The ID of the Shared Drive, if applicable. Defaults to None.
        
    Raises:
        HttpError: If the Google API fundamentally rejects the copy request.
    """
    copy_metadata = {
        'name': new_name,
        'parents': [parent_id]
    }
    try:
        service.files().copy(
            fileId=file_id,
            body=copy_metadata,
            supportsAllDrives=True
        ).execute()
    except HttpError as e:
        log.error(f"Failed to copy file {file_id}: {e}")
        raise

def delete_file(service: Resource, file_id: str) -> None:
    """
    Deletes a file or folder permanently.

    Args:
        service (Resource): Authenticated Google Drive service object.
        file_id (str): The Drive ID of the file or folder to delete.
        
    Raises:
        Exception: Upon any failure to delete the requested asset.
    """
    try:
        service.files().delete(
            fileId=file_id,
            supportsAllDrives=True
        ).execute()
    except Exception as e:
        log.error(f"Failed to delete {file_id}: {e}")
        raise
