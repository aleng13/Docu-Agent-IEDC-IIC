"""Lightweight keep-alive Flask server for Render Web Service health checks."""

import logging
import os
import threading
from collections import deque
from typing import Optional

from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
_server_thread: Optional[threading.Thread] = None
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_FILE_PATH = os.path.join(_PROJECT_ROOT, "bot.log")
_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Docu-Agent Dashboard</title>
    <style>
        :root {
            --bg: #0b0f14;
            --panel: #121821;
            --border: #1f2a37;
            --text: #e5e7eb;
            --muted: #9ca3af;
            --accent: #22c55e;
        }
        * {
            box-sizing: border-box;
        }
        body {
            margin: 0;
            min-height: 100vh;
            background: radial-gradient(circle at top right, #1a2230 0%, var(--bg) 55%);
            color: var(--text);
            font-family: "Segoe UI", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
            padding: 24px;
        }
        .card {
            max-width: 1040px;
            margin: 0 auto;
            background: linear-gradient(180deg, #151e2b 0%, var(--panel) 100%);
            border: 1px solid var(--border);
            border-radius: 14px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
            overflow: hidden;
        }
        .header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: baseline;
            justify-content: space-between;
        }
        .title {
            margin: 0;
            font-size: 1.15rem;
            letter-spacing: 0.2px;
        }
        .meta {
            margin: 0;
            color: var(--muted);
            font-size: 0.9rem;
        }
        .terminal {
            margin: 16px;
            padding: 16px;
            background: #05080c;
            border: 1px solid #15202b;
            border-radius: 10px;
            height: min(72vh, 680px);
            overflow-y: auto;
            white-space: pre-wrap;
            line-height: 1.4;
            font-family: Consolas, "Courier New", monospace;
            color: var(--accent);
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1 class="title">Docu-Agent Live Logs</h1>
            <p class="meta" id="status">Updating every 2s</p>
        </div>
        <pre class="terminal" id="logTerminal">Initializing logs...</pre>
    </div>

    <script>
        const terminal = document.getElementById("logTerminal");
        const statusText = document.getElementById("status");

        async function refreshLogs() {
            try {
                const response = await fetch("/api/logs", { cache: "no-store" });
                const payload = await response.json();
                terminal.textContent = payload.logs || "Initializing logs...";
                terminal.scrollTop = terminal.scrollHeight;
                statusText.textContent = "Updating every 2s";
            } catch (error) {
                statusText.textContent = "Log stream unavailable";
            }
        }

        refreshLogs();
        setInterval(refreshLogs, 2000);
    </script>
</body>
</html>
"""


@app.route("/")
def home() -> str:
    """Renders the live dashboard UI.

    Returns:
        str: HTML dashboard with auto-updating logs.
    """
    return render_template_string(_DASHBOARD_TEMPLATE)


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
