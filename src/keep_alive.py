"""Lightweight keep-alive Flask server for Render Web Service health checks."""

import logging
import os
import threading
from typing import Optional

from flask import Flask

app = Flask(__name__)
_server_thread: Optional[threading.Thread] = None


@app.route("/")
def home() -> str:
    """Returns a simple liveness message for health checks.

    Returns:
        str: Static liveness response.
    """
    return "Docu-Agent Bot is alive and running!"


def _run_server() -> None:
    """Runs Flask on a Render-compatible host and dynamic port.

    Returns:
        None
    """
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


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
