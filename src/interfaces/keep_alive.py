import logging
import os
import threading
import json
import time
from collections import deque
from typing import Optional, Dict, Any

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

from src.core.drive_auth import get_drive_service, get_sheets_service
from src.core.drive_client import find_folder_id
from src.core import sheets_client
from src.core.config import get_project_root
from src.tools.folder_logic import create_event_folder
from src.tools.summary_extractor import extract_event_details

load_dotenv()
_SHARED_DRIVE_ID = os.getenv("SHARED_DRIVE_ID")

app = Flask(__name__)
_server_thread: Optional[threading.Thread] = None
_PROJECT_ROOT = get_project_root()
_LOG_FILE_PATH = os.path.join(_PROJECT_ROOT, "bot.log")
_LAST_SUMMARY_RESULT: Optional[Dict[str, Any]] = None

def get_config_ids() -> Dict[str, Optional[str]]:
    """Retrieves the required folder IDs from config.json or environment."""
    config_path = os.path.join(_PROJECT_ROOT, "config.json")
    parent_id = os.getenv("PARENT_FOLDER_ID")
    template_id = os.getenv("TEMPLATE_FOLDER_ID")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            parent_id = parent_id or config.get("parent_folder_id")
            template_id = template_id or config.get("template_folder_id")
    except Exception as e:
        app.logger.warning(f"Could not load from config.json: {e}")

    return {"parent_id": parent_id, "template_id": template_id}


def _reset_log_file(event_name: str, action_label: str) -> None:
    """Creates a fresh log file for the active UI job."""
    with open(_LOG_FILE_PATH, "w", encoding="utf-8") as f:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - WEB_STATUS - INFO - Initializing {action_label} for '{event_name}'...\n")


def _append_log(message: str) -> None:
    """Appends a timestamped line to the web log file."""
    with open(_LOG_FILE_PATH, "a", encoding="utf-8") as f:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - WEB_STATUS - INFO - {message}\n")

@app.route("/")
def home() -> str:
    """Renders the UI from index.html template."""
    return render_template("index.html")
@app.route("/api/logs")
def get_logs() -> object:
    """Returns the last 100 log lines as JSON.

    Returns:
        object: Flask JSON response with a `logs` string field.
    """
    try:
        with open(_LOG_FILE_PATH, "r", encoding="utf-8") as log_file:
            tail_lines = deque(log_file, maxlen=100)
        return jsonify({"logs": "".join(tail_lines).rstrip() or "Initializing logs..."})
    except FileNotFoundError:
        return jsonify({"logs": "Initializing logs..."})
    except Exception as e:
        return jsonify({"logs": f"Log read error: {str(e)}"})


@app.route("/api/create", methods=["POST"])
def api_create_event():
    """Trigger folder creation asynchronously via POST."""
    data = request.get_json()
    event_name = data.get("event_name") if data else None

    if not event_name:
        return jsonify({"error": "Event Name is required"}), 400

    def background_worker():
        """Worker thread for folder creation."""
        logging.info(f"WEB_THREAD: Initializing creation for '{event_name}'")
        
        ids = get_config_ids()
        parent_id = ids["parent_id"]
        template_id = ids["template_id"]

        if not parent_id or not template_id:
            logging.error("WEB_THREAD: Config Error - Missing parent_id or template_id.")
            return

        _reset_log_file(event_name, "folder creation")

        try:
            service = get_drive_service(_PROJECT_ROOT)
            
            def log_progress(status: str):
                """Callback to write progress to log file."""
                with open(_LOG_FILE_PATH, "a", encoding="utf-8") as f:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"{timestamp} - WEB_STATUS - INFO - {status}\n")

            folder_id = create_event_folder(
                service=service,
                event_name=event_name,
                template_id=template_id,
                parent_id=parent_id,
                shared_drive_id=_SHARED_DRIVE_ID,
                on_progress=log_progress
            )
            
            if folder_id:
                log_progress(f"DEPLOYMENT_COMPLETE: {folder_id}")
            else:
                log_progress("FAILED: Folder creation failed.")

        except Exception as e:
            logging.exception(f"WEB_THREAD Error: {e}")
            _append_log(f"ERROR: {str(e)}")

    thread = threading.Thread(target=background_worker, daemon=True)
    thread.start()
    
    return jsonify({"status": "Creation started", "event_name": event_name}), 202


@app.route("/api/summary", methods=["POST"])
def api_run_summary():
    """Trigger summary extraction asynchronously via POST."""
    data = request.get_json()
    event_name = data.get("event_name") if data else None

    if not event_name:
        return jsonify({"error": "Event Name is required"}), 400

    def background_worker():
        """Worker thread for summary extraction."""
        global _LAST_SUMMARY_RESULT

        logging.info(f"WEB_THREAD: Initializing summary for '{event_name}'")

        ids = get_config_ids()
        parent_id = ids["parent_id"]
        template_id = ids["template_id"]

        if not parent_id or not template_id:
            logging.error("WEB_THREAD: Config Error - Missing parent_id or template_id.")
            _reset_log_file(event_name, "summary extraction")
            _append_log("FAILED: Config error - missing parent_id or template_id.")
            return

        _reset_log_file(event_name, "summary extraction")

        try:
            drive_service = get_drive_service(_PROJECT_ROOT)
            sheets_service = get_sheets_service(_PROJECT_ROOT)

            def log_progress(status: str):
                """Callback to write progress to log file."""
                _append_log(status)

            shared_drive_id = _SHARED_DRIVE_ID
            folder_id = find_folder_id(
                drive_service,
                event_name,
                parent_id,
                shared_drive_id=shared_drive_id,
            )

            if not folder_id:
                log_progress("FAILED: Event folder not found.")
                return

            log_progress(f"Found event folder: {folder_id}")
            log_progress("Reading report, committee, registration, and feedback data...")

            extracted_data = extract_event_details(
                drive_service,
                sheets_service,
                folder_id,
                event_name,
                shared_drive_id=shared_drive_id,
            )

            if not extracted_data or "error" in extracted_data or "Error" in extracted_data.get("Status", ""):
                log_progress(f"FAILED: Summary extraction failed - {extracted_data.get('Status', 'Unknown error') if extracted_data else 'Unknown error'}")
                return

            config_path = os.path.join(_PROJECT_ROOT, "config.json")
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            sheet_id = config.get("activity_sheet", {}).get("sheet_id")
            if not sheet_id:
                log_progress("FAILED: Missing Activity Sheet ID in config.json.")
                return

            row = sheets_client.find_event_row(sheets_service, sheet_id, event_name, config)
            if not row:
                log_progress("FAILED: Event row not found in the Activity Sheet.")
                return

            success = sheets_client.update_event_row(sheets_service, sheet_id, row, extracted_data, config)
            if not success:
                log_progress("FAILED: Could not write summary data to the Activity Sheet.")
                return

            _LAST_SUMMARY_RESULT = {
                "event_name": event_name,
                "folder_id": folder_id,
                "row": row,
                "activity_sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
                "summary": extracted_data,
            }

            preview_fields = {
                "Event Name": extracted_data.get("Event Name"),
                "Event Date": extracted_data.get("Event Date"),
                "No. of Participants": extracted_data.get("No. of Participants"),
                "Percentage Participation": extracted_data.get("Percentage Participation"),
                "Coordinators": extracted_data.get("Coordinators"),
            }
            log_progress("SUMMARY_COMPLETE")
            log_progress(f"SUMMARY_PREVIEW: {json.dumps(preview_fields, ensure_ascii=True)}")

        except Exception as e:
            logging.exception(f"WEB_THREAD Summary Error: {e}")
            _append_log(f"FAILED: {str(e)}")

    thread = threading.Thread(target=background_worker, daemon=True)
    thread.start()

    return jsonify({"status": "Summary extraction started", "event_name": event_name}), 202


@app.route("/api/summary-result")
def get_summary_result():
    """Returns the most recent summary result payload."""
    if not _LAST_SUMMARY_RESULT:
        return jsonify({"error": "No summary result available"}), 404
    return jsonify(_LAST_SUMMARY_RESULT)


def _run_server() -> None:
    """Runs Flask on a Render-compatible host and dynamic port.

    Returns:
        None
    """
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    port = int(os.environ.get("PORT", 8080))
    print(f"\n🚀 Docu-Agent Dashboard is LIVE!")
    print(f"🔗 Click here to open: http://localhost:{port}\n")
    # debug=True enables auto-reload and better error reporting
    app.run(host="0.0.0.0", port=port, debug=True)


def keep_alive() -> None:
    """Starts the keep-alive Flask server in a non-blocking daemon thread.

    Returns:
        None
    """
    global _server_thread

    if _server_thread and _server_thread.is_alive():
        return

    _server_thread = threading.Thread(target=_run_server, daemon=True)
    _server_thread.start()


if __name__ == "__main__":
    # If run directly, run the server in the main thread (blocking)
    _run_server()

