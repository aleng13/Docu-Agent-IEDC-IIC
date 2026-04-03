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

from src.core.drive_auth import get_drive_service, get_credentials
from src.tools.folder_logic import create_event_folder
from src.core.config import load_config
from src.core.drive_client import find_folder_id
from googleapiclient.discovery import build
import src.core.sheets_client as sheets_client
from src.tools.summary_extractor import extract_event_details

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

def _parse_args() -> argparse.Namespace:
    argv = sys.argv[1:]
    if argv and argv[0] not in ("create", "summary"):
        argv = ["create"] + argv

    parser = argparse.ArgumentParser(
        description="Docu-Agent-Clean CLI (folder creation and summary extraction)."
    )
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser(
        "create", help="Create a new Google Drive event folder from a template."
    )
    create_parser.add_argument(
        "event_name", type=str, help="The name of the event (e.g., 'My Event Header')"
    )

    summary_parser = subparsers.add_parser(
        "summary", help="Extract summary data and write it to the Activity Sheet."
    )
    summary_parser.add_argument(
        "event_name", type=str, help="The name of the event (e.g., 'My Event Header')"
    )

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)
    return args


def _run_create(event_name: str) -> None:
    load_dotenv()
    shared_drive_id = os.getenv("SHARED_DRIVE_ID")

    project_root = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(project_root, "config.json")

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
            event_name=event_name,
            template_id=template_id,
            parent_id=parent_id,
            shared_drive_id=shared_drive_id,
        )

        if new_folder_id:
            log.info(f"Success! Folder created with ID: {new_folder_id}")
        else:
            log.error("Folder creation failed or folder already exists.")
            sys.exit(1)

    except Exception as e:
        log.error(f"An error occurred: {e}")
        sys.exit(1)


def _run_summary(event_name: str) -> None:
    load_dotenv()
    config = load_config()
    if not config:
        log.error("Failed to load config.json.")
        sys.exit(1)

    activity_config = config.get("activity_sheet")
    if not activity_config:
        log.error("Missing activity_sheet config in config.json.")
        sys.exit(1)

    sheet_id = activity_config.get("sheet_id")
    if not sheet_id:
        log.error("Missing activity_sheet.sheet_id in config.json.")
        sys.exit(1)

    try:
        project_root = os.path.dirname(os.path.abspath(__file__))
        drive_service = get_drive_service(project_root)
        
        creds = get_credentials(project_root)
        sheets_service = build('sheets', 'v4', credentials=creds)

        parent_id = config.get("parent_folder_id")
        if not parent_id:
            log.error("Missing parent_folder_id in config.json.")
            sys.exit(1)
            
        shared_drive_id = os.getenv("SHARED_DRIVE_ID")

        folder_id = find_folder_id(drive_service, event_name, parent_id, shared_drive_id)
        if not folder_id:
            log.error(f"Event folder not found: {event_name}")
            sys.exit(1)

        data = extract_event_details(drive_service, sheets_service, folder_id, event_name, shared_drive_id)
        if "error" in data or "Error" in data.get("Status", ""):
            log.error(f"Summary extraction failed: {data}")
            sys.exit(1)

        row = sheets_client.find_event_row(sheets_service, sheet_id, event_name, config)
        if not row:
            log.error("Event row not found in the Activity Sheet.")
            sys.exit(1)

        success = sheets_client.update_event_row(sheets_service, sheet_id, row, data, config)
        if not success:
            log.error("Failed to update the Activity Sheet.")
            sys.exit(1)

        log.info("Summary saved successfully.")
        preview_keys = [
            "Event Date",
            "No. of Participants",
            "Coordinators",
            "Percentage Participation",
        ]
        for key in preview_keys:
            if key in data:
                log.info(f"{key}: {data.get(key)}")

    except Exception as e:
        log.error(f"An error occurred: {e}")
        sys.exit(1)


def main() -> None:
    args = _parse_args()
    if args.command == "create":
        _run_create(args.event_name)
        return
    if args.command == "summary":
        _run_summary(args.event_name)
        return

if __name__ == "__main__":
    main()
