# Full Run Guide: Docu-Agent-Clean

This guide provides a step-by-step walkthrough for setting up and running the Docu-Agent-Clean system from scratch.

---

## 1. Local Environment Setup

### 1.1 Install Python
Ensure you have **Python 3.11 or higher** installed. You can check your version with:
```bash
python --version
```

### 1.2 Create a Virtual Environment
It is highly recommended to use a virtual environment to manage dependencies:
```bash
# Create the environment
python -m venv venv

# Activate it (Windows)
.\venv\Scripts\activate

# Activate it (MacOS/Linux)
source venv/bin/activate
```

### 1.3 Install Dependencies
Install all required libraries using the provided `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## 2. Google Cloud Platform (GCP) Configuration

The bot requires access to the Google Drive API to manage files.

1. **Create a Project**: Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2. **Enable APIs**: Enable the **Google Drive API** and **Google Sheets API** for your project.
3. **Configure OAuth Screen**: Set up an "External" OAuth consent screen and add yourself as a test user.
4. **Create Credentials**:
   - Go to **Credentials** -> **Create Credentials** -> **OAuth client ID**.
   - Select **Desktop App** as the type.
   - Download the JSON file and rename it to `credentials.json`.
5. **Place the file**: Save `credentials.json` in the root of the `Docu-Agent-Clean` folder.

> [!IMPORTANT]
> On the first run, the program will open your browser to ask for permission. Once authenticated, it will generate a `token.json` file so you don't have to log in again.

---

## 3. Configuration Files

### 3.1 `.env` File
Create a `.env` file in the root directory:
```env
SHARED_DRIVE_ID=your_shared_drive_id (leave empty if not using a shared drive)
```

### 3.2 `config.json`
Update the following fields in `config.json`:
- `gemini_api_key`: Your Google AI Studio API key (for document validation).
- `template_folder_id`: The ID of the folder containing your templates.
- `parent_folder_id`: The ID of the folder where new event folders should be created.

---

## 4. Running the Program

### Method A: CLI Mode (One-off Creation)
Best for quick, local tests.
```bash
python main.py "My Event Name"
```

### Method A2: CLI Summary Mode (Write to Sheet)
Runs summary extraction and writes results to the Activity Sheet by default.
```bash
python main.py summary "My Event Name"
```

### Method B: Web Dashboard Mode (Standalone)
If you want to run the web-based status dashboard:
```bash
python -m src.interfaces.keep_alive
```
The dashboard will be available at `http://localhost:8080` (unless a different `PORT` is set in `.env`).

---

## 5. Troubleshooting

- **`ModuleNotFoundError: No module named 'src'`**: Ensure you are running commands from the project root.
- **`HttpError 403: Rate Limit Exceeded`**: The bot has built-in delays, but if this happens, restart the process.
- **Credential Errors**: Delete `token.json` and run the program again to re-authenticate.
