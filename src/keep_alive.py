import logging
import os
import threading
import json
import time
from collections import deque
from typing import Optional, Dict

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

from src.drive_auth import get_drive_service
from src.folder_logic import create_event_folder

load_dotenv()
_SHARED_DRIVE_ID = os.getenv("SHARED_DRIVE_ID")

app = Flask(__name__)
_server_thread: Optional[threading.Thread] = None
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_FILE_PATH = os.path.join(_PROJECT_ROOT, "bot.log")

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
    return {"parent_id": parent_id, "template_id": template_id}

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
            with open(_LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(f"ERROR: {str(e)}\n")

    thread = threading.Thread(target=background_worker, daemon=True)
    thread.start()
    
    return jsonify({"status": "Creation started", "event_name": event_name}), 202


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

