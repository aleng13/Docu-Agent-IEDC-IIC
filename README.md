# Docu-Agent: Vibe Edition

Docu-Agent-Clean is an automated Google Drive infrastructure bot that flawlessly clones, namespaces, and contextualizes template folders for operational events. Designed around strict idempotent API logic, it prevents manual data-entry errors through transactional Google Drive setups.

## Prerequisites

- Python 3.11+
- A Google Cloud Service Account `credentials.json` (OAuth2.0 enabled) stored in the root folder.
- Google Account ready to authenticate the app locally at first run.

## Quick Start

1. **Setup Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Configure GCP**: Drop your `credentials.json` into the root.

3. **Detailed Documentation**: For a full, step-by-step setup (including Telegram and GEMINI setup), please see our **[Comprehensive Run Guide](docs/RUN_GUIDE.md)**.

## Running the App

### CLI Mode (One-off)
```bash
python main.py "My Cool Event 2026"
```

### CLI Summary Mode (Write to Sheet)
```bash
python main.py summary "My Cool Event 2026"
```
This writes the extracted summary directly to the Activity Sheet and prints a short preview.

### Telegram Bot Mode (Polling)
```bash
python -m src.interfaces.telegram_bot
```

### Web Dashboard Mode (Standalone)
```bash
python -m src.interfaces.keep_alive
```
