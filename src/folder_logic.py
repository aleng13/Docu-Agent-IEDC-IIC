"""
Folder Logic Module
-------------------
Implements business rules for Drive folder creation, such as idempotency,
smart recursive duplication of template directories, and transactional rollbacks.
"""

import logging
import time
from typing import Optional, Callable
from googleapiclient.discovery import Resource

from .drive_client import (
    find_folder_id, 
    create_folder, 
    update_folder_color,
    list_files_in_folder,
    copy_file,
    delete_file
)

log = logging.getLogger(__name__)

API_RATE_LIMIT_DELAY = 0.5 
NEW_FOLDER_COLOR = '#ff7537' # Orange
NO_RENAME_KEYWORDS = ["sample", "template", "instructions", "guidelines"]

def should_rename_file(file_name: str) -> bool:
    """
    Checks if a file should receive the event name prefix.

    Args:
        file_name (str): The original filename from the template.

    Returns:
        bool: True if the file should be renamed; False if it contains restricted keywords.
    """
    for keyword in NO_RENAME_KEYWORDS:
        if keyword.lower() in file_name.lower():
            return False
    return True

def copy_folder_recursively(service: Resource, event_name: str, source_folder_id: str, 
                            destination_folder_id: str, shared_drive_id: Optional[str] = None,
                            on_progress: Optional[Callable[[str], None]] = None) -> None:
    """
    Recursively deep-copies a template directory into a target directory using DFS.
    
    Files are intelligently renamed with the `event_name` prefix unless they contain
    keywords from NO_RENAME_KEYWORDS.

    Args:
        service (Resource): Authenticated Google Drive service object.
        event_name (str): The prefix to add to copied files (e.g., "TechTalk_").
        source_folder_id (str): The Drive ID of the template folder/subfolder.
        destination_folder_id (str): The Drive ID of the newly created destination folder/subfolder.
        shared_drive_id (Optional[str]): The ID of the Shared Drive, if applicable. Defaults to None.
        on_progress (Optional[Callable[[str], None]]): Optional callback for progress updates.
        
    Raises:
        Exception: If a subfolder creation or file copy critically fails.
    """
    log.info(f"📂 Reading contents of folder: {source_folder_id}")
    
    try:
        items = list_files_in_folder(service, source_folder_id, shared_drive_id)
        
        for item in items:
            time.sleep(API_RATE_LIMIT_DELAY)
            
            item_id = item['id']
            item_name = item['name']
            item_mime = item['mimeType']
            
            if item_mime == 'application/vnd.google-apps.folder':
                log.info(f"📂 Creating subfolder: '{item_name}'")
                if on_progress:
                    on_progress(f"Creating folder: {item_name}")
                new_subfolder_id = create_folder(service, item_name, destination_folder_id, shared_drive_id)
                
                if not new_subfolder_id:
                    raise Exception(f"Subfolder creation failed: {item_name}")

                copy_folder_recursively(
                    service,
                    event_name,
                    item_id,
                    new_subfolder_id,
                    shared_drive_id,
                    on_progress
                )
            else:
                if item_mime in ['application/vnd.google-apps.map', 'application/vnd.google-apps.site']:
                    log.warning(f"⚠️ Skipping non-copyable type: {item_name}")
                    continue

                if should_rename_file(item_name):
                    new_file_name = f"{event_name}_{item_name}"
                else:
                    new_file_name = item_name

                log.info(f"   📝 Copying file: {new_file_name}")
                if on_progress:
                    on_progress(f"Copying: {new_file_name}")
                copy_file(service, item_id, new_file_name, destination_folder_id, shared_drive_id)

    except Exception as e:
        log.error(f"❌ Error in recursion loop: {e}")
        raise


def create_event_folder(service: Resource, event_name: str, template_id: str, 
                        parent_id: str, shared_drive_id: Optional[str] = None,
                        on_progress: Optional[Callable[[str], None]] = None) -> Optional[str]:
    """
    Orchestrates the creation and setup of a new event folder.
    
    Performs idempotency checks to avoid duplicates. Deep-copies a defined template 
    structure into the newly created folder, and dynamically rolls back the entire 
    creation transaction if an exception is encountered.

    Args:
        service (Resource): Authenticated Google Drive service object.
        event_name (str): The human-readable name of the event (e.g. 'Tech Workshop 2026').
        template_id (str): The Drive ID of the template folder to clone.
        parent_id (str): The Drive ID of the directory where the new folder will sit.
        shared_drive_id (Optional[str]): The ID of the Shared Drive context, if applicable. Defaults to None.
        on_progress (Optional[Callable[[str], None]]): Optional callback for progress updates.

    Returns:
        Optional[str]: The Drive ID of the fully constructed folder, or None if the operation failed.
    """
    new_folder_id = None
    
    try:
        log.info(f"🚀 Starting folder creation for: '{event_name}'")
        if on_progress:
            on_progress("Initializing creation...")

        existing_id = find_folder_id(service, event_name, parent_id, shared_drive_id)
        if existing_id:
            log.warning(f"⚠️ Folder '{event_name}' already exists. Skipping creation.")
            return existing_id

        log.info(f"🚀 Creating root event folder: '{event_name}' in parent '{parent_id}'")
        if on_progress:
            on_progress("Creating root folder...")
        new_folder_id = create_folder(service, event_name, parent_id, shared_drive_id)
        
        if not new_folder_id:
            log.error(f"❌ Failed to create root event folder for '{event_name}'")
            return None
        
        update_folder_color(service, new_folder_id, NEW_FOLDER_COLOR)
        log.info(f"✅ Root folder created (ID: {new_folder_id})")

        log.info("Starting template copy...")
        if on_progress:
            on_progress("Cloning template contents...")
        copy_folder_recursively(
            service, 
            event_name, 
            template_id, 
            new_folder_id,
            shared_drive_id,
            on_progress
        )
        
        log.info(f"🎉 Successfully created event infrastructure for '{event_name}'")
        return new_folder_id

    except Exception as e:
        log.error(f"❌ CRITICAL ERROR in create_event_folder: {e}")
        
        if new_folder_id:
            log.warning(f"🔄 Rolling back: Deleting incomplete folder {new_folder_id}...")
            try:
                delete_file(service, new_folder_id)
                log.info("✅ Rollback successful. System state is clean.")
            except Exception as cleanup_error:
                log.error(f"💀 FATAL: Rollback failed. Manual cleanup required for {new_folder_id}. Error: {cleanup_error}")
        
        return None
