"""
Docu-Agent Main CLI Entrypoint
------------------------------
A terminal executable script to spin up the entire Docu-Agent-Clean folder logic.
Usage: python main.py "Event Name Here"
"""

import os
import sys
import argparse
import logging
import json
from dotenv import load_dotenv

from src.drive_auth import get_drive_service
from src.folder_logic import create_event_folder

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

def main() -> None:
    """
    Parses CLI arguments, extracts environment config, initializes Drive API
    services, and triggers the folder creation pipeline.
    """
    parser = argparse.ArgumentParser(description="Create a new Google Drive event folder from a template.")
    parser.add_argument("event_name", type=str, help="The name of the event (e.g., 'My Event Header')")
    args = parser.parse_args()

    # Load from .env for sensitive/environment-specific variables
    load_dotenv()
    shared_drive_id = os.getenv("SHARED_DRIVE_ID")
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(project_root, "config.json")
    
    # Load from config.json
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            template_id = config.get("template_folder_id")
            parent_id = config.get("parent_folder_id")
    except Exception as e:
        log.error(f"Failed to read config.json: {e}")
        sys.exit(1)

    if not template_id or not parent_id:
        log.error("Missing template_folder_id or parent_folder_id in config.json.")
        sys.exit(1)

    try:
        service = get_drive_service(project_root)
        new_folder_id = create_event_folder(
            service=service,
            event_name=args.event_name,
            template_id=template_id,
            parent_id=parent_id,
            shared_drive_id=shared_drive_id
        )

        if new_folder_id:
            log.info(f"Success! Folder created with ID: {new_folder_id}")
        else:
            log.error("Folder creation failed or folder already exists.")
            sys.exit(1)

    except Exception as e:
        log.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
