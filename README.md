# Docu-Agent: Vibe Edition

Docu-Agent-Clean is an automated Google Drive infrastructure bot that flawlessly clones, namespaces, and contextualizes template folders for operational events. Designed around strict idempotent API logic, it prevents manual data-entry errors through transactional Google Drive setups.

## Prerequisites

- Python 3.11+
- A Google Cloud Service Account `credentials.json` (OAuth2.0 enabled) stored in the root folder.
- Google Account ready to authenticate the app locally at first run.

## Setup Instructions

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # MacOS/Linux
   source venv/bin/activate
   ```

2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize Configuration:**
   - Drop your `credentials.json` file into the root directory.
   - Adjust `config.json` with your target template structure and IDs.
   - Setup `.env` as defined below.

## Environment Variables
Create a file named `.env` in the root folder and add the following keys. **Never commit actual credentials or tokens to version control.**

```env
TELEGRAM_TOKEN=your_telegram_bot_token
SHARED_DRIVE_ID=your_target_shared_drive_id
```

## Running the App

```bash
python main.py "My Cool Event 2026"
```
