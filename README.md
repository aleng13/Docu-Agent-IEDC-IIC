# Docu-Agent: Vibe Edition

Docu-Agent-Clean is an automated Google Drive infrastructure tool that clones, namespaces, and contextualizes template folders for operational events. Designed around strict idempotent API logic, it prevents manual data-entry errors through transactional Google Drive setups.

## Prerequisites

- Python 3.11+
- A Google OAuth Desktop App `credentials.json` stored in the project root.
- A Google account with access to your target Drive folders and Activity Sheet.
- A valid `config.json` with `template_folder_id`, `parent_folder_id`, and `activity_sheet` settings.

## Quick Start

1. **Setup Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Configure OAuth**: Drop your `credentials.json` into the root.
   On first run, a browser login opens and a `token.json` is generated automatically.

3. **Detailed Documentation**: For a full, step-by-step setup, please see our **[Comprehensive Run Guide](docs/RUN_GUIDE.md)**.

## Running the App

### CLI Mode (Create Event Folder)
```bash
python main.py "My Cool Event 2026"
```

### CLI Summary Mode (Write to Sheet)
```bash
python main.py summary "My Cool Event 2026"
```
This writes the extracted summary directly to the Activity Sheet and prints a short preview.

### Web Dashboard Mode (Standalone)
```bash
python -m src.interfaces.keep_alive
```
Dashboard URL: `http://localhost:8080`
