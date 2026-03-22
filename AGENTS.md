# Docu-Agent-Clean AI Handbook

This is the central rulebook for interacting with, expanding, or refactoring the `Docu-Agent-Clean` ecosystem. If you are an AI assistant (like Cursor, Copilot, or Codex) taking a prompt from a human engineer, **strictly adhere to the following architecture and style guidelines.**

## Core Architecture Principles

1. **No Global Configurations Deep in Code**: 
   - Never inject `os.getenv` or generic `config.json` bindings deep into the submodules (`src/`). Configuration arguments must always be surfaced locally in `main.py` and passed down distinctly as strongly-typed function arguments (like `template_id: str`).
2. **Absolute Module Isolation**:
   - `drive_auth.py` strictly manages the OAuth tokens.
   - `drive_client.py` contains strictly atomic API wrappers around the `googleapiclient`. They should just perform the HTTP operations and yield back responses. No business logic belongs here.
   - `folder_logic.py` takes the atomic wrappers and combines them to execute business logic (like recursively walking the filesystem, checking constraints based on `NO_RENAME_KEYWORDS`, etc).

## Code Style & Formatting Rules

- **Strict Type Hints**: Every function parameter and return type must be strongly typed using Python's `typing` module! `list` or `dict` aren't enough; use `List[Dict[str, Any]]` or `Optional[str]`.
- **Google-Style Docstrings**: Every function and module *must* contain a thorough Google-Style docstring explaining its capabilities, `Args:`, `Returns:`, and potential `Raises:`.
- **Idempotency**: All new business logic operations on external state (Google Drive files, Google Sheets) must be strictly idempotent. If the script fails halfway, provide rollback logic in the `try-except` shell.

## Adding Features

If you are asked to implement a new feature (like downloading PDFs from Google Drive), follow this trace:
1. Add the atomic Drive API wrapper to `src/drive_client.py` (e.g. `download_file(...)`).
2. Implement your business checks, validations, or recursion in `src/folder_logic.py`.
3. Wire the required credentials and CLI inputs through `main.py`.
