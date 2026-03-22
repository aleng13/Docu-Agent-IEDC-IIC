# Configuration Guide

The `config.json` file located in the root handles the business-level logic for document tracking and verification. **It is critical to maintain the integrity of this JSON schema - any syntax breaks will crash the app.**

### Base Configuration
- `gemini_api_key`: The active Developer API key utilized exclusively by the AI inspection agent during event report checks.
- `template_folder_id`: The Google Drive ID matching the Root folder of the primary standard template.
- `parent_folder_id`: The Google Drive ID detailing where all cloned events will live.

### `activity_sheet`
The metadata linking the final destination tracker for the output logs.
- `sheet_id`: Google Sheets destination ID.
- `sheet_name`: Destination tab.
- `event_name_column`: Where the human-readable String exists.
- `data_start_row`: The row immediately following headers where ingestion begins.
- `column_map`: A definitive mapping of field definitions dictating which physical column letter a specific datapoint aligns with.

### `template_structure`
Holds strict rules dictating what validation steps the Docu-Agent imposes during end-of-lifecycle auditing for folder hygiene.

- `type`: Defines the checking methodology:
   - `form_and_sheet_check`: Validates linked forms and response sheets exist.
   - `content_check`: Sweeps Docs and Sheets for placeholder strings indicating human neglect.
   - `sheet_check`: Sweeps sheets.
   - `template_and_upload`: Asserts file presence inside required subfolders matching specified file extensions (`upload_extensions` or `allowed_extensions`).
   - `gemini_docx_report_check` / `gemini_poster_validation`: Pipes complex document texts or direct image files into the Gemini LLM for AI compliance grading using the defined `prompt`.

#### Key Warning on Prompts
The `prompt` parameters under `gemini_` methods utilize standard fast-formatted Python string injection via `{event_name}`. Modifying this must not break the f-string formatting logic. The AI depends on this context explicitly to grade document relevance.
