"""Google Drive and Sheets authentication using OAuth credentials."""

import logging
import os
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from src.core.config import get_project_root

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


def get_credentials(project_root: Optional[str] = None) -> Credentials:
    """Load OAuth credentials from token.json or run login via browser.

    Args:
        project_root: Optional absolute path to project root. If omitted, it is auto-resolved.

    Returns:
        Credentials: Authenticated OAuth credentials.

    Raises:
        FileNotFoundError: If `credentials.json` is missing in the project root.
    """
    if not project_root:
        project_root = get_project_root()

    token_path = os.path.join(project_root, TOKEN_FILE)
    credentials_path = os.path.join(project_root, CREDENTIALS_FILE)

    creds: Optional[Credentials] = None
    if os.path.exists(token_path):
        log.info("Loading OAuth token from token.json")
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing expired OAuth token")
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"credentials.json not found at {credentials_path}."
                )

            log.info("Starting OAuth browser login flow")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
        log.info("OAuth token saved to token.json")

    return creds


def get_drive_service(project_root: Optional[str] = None) -> Resource:
    """Build an authenticated Google Drive API service object.

    Args:
        project_root: Optional absolute path to project root.

    Returns:
        Resource: Google Drive API v3 service client.
    """
    creds = get_credentials(project_root)
    service = build("drive", "v3", credentials=creds)
    log.info("Drive service initialized successfully.")
    return service


def get_sheets_service(project_root: Optional[str] = None) -> Resource:
    """Build an authenticated Google Sheets API service object.

    Args:
        project_root: Optional absolute path to project root.

    Returns:
        Resource: Google Sheets API v4 service client.
    """
    creds = get_credentials(project_root)
    service = build("sheets", "v4", credentials=creds)
    log.info("Sheets service initialized successfully.")
    return service
