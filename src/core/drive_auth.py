"""
Authentication Module
---------------------
Handles Google OAuth 2.0 flow and token management for Google Drive and Google Sheets.
Unified from the previous GoogleAuth and DriveAuth split.
"""

import os
import pickle
import logging
from typing import Any, Optional

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import Resource, build
from src.core.config import get_project_root

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"

def get_credentials(project_root: Optional[str] = None) -> Any:
    """
    Loads Google API credentials from token.json or initiates an OAuth flow.

    Args:
        project_root: Optional absolute path to project root. Defaults to config auto-resolution.

    Returns:
        Any: An authenticated Google credentials object.
        
    Raises:
        FileNotFoundError: If credentials.json is missing.
    """
    if not project_root:
        project_root = get_project_root()
        
    token_path = os.path.join(project_root, TOKEN_FILE)
    creds_path = os.path.join(project_root, CREDENTIALS_FILE)

    creds = None

    if os.path.exists(token_path):
        log.info("🔑 Loading OAuth token.json")
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("🔄 Refreshing expired token")
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(
                    f"credentials.json not found at {creds_path}. Download it from Google Cloud Console."
                )

            log.info("🌐 Starting OAuth login flow")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "wb") as token:
            pickle.dump(creds, token)
            log.info("💾 token.json saved")

    return creds

def get_drive_service(project_root: Optional[str] = None) -> Resource:
    """
    Returns an authenticated Google Drive service object.
    
    Args:
        project_root: Optional absolute path to project root.
    """
    creds = get_credentials(project_root)
    service = build("drive", "v3", credentials=creds)
    log.info("✅ Drive service initialized successfully.")
    return service

def get_sheets_service(project_root: Optional[str] = None) -> Resource:
    """
    Returns an authenticated Google Sheets service object.
    
    Args:
        project_root: Optional absolute path to project root.
    """
    creds = get_credentials(project_root)
    service = build("sheets", "v4", credentials=creds)
    log.info("✅ Sheets service initialized successfully.")
    return service
