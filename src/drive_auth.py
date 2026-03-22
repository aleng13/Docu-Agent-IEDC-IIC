"""
Authentication Module
---------------------
Handles Google OAuth 2.0 flow and token management for Google Drive.
"""

import os
import pickle
import logging
from typing import Any
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import Resource, build

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_credentials(project_root: str) -> Any:
    """
    Loads Google API credentials from token.json or initiates an OAuth flow.

    Args:
        project_root (str): The absolute path to the project root directory containing credentials.json.

    Returns:
        Any: An authenticated Google credentials object.
        
    Raises:
        FileNotFoundError: If credentials.json is missing when a new login is required.
    """
    token_path = os.path.join(project_root, "token.json")
    creds_path = os.path.join(project_root, "credentials.json")

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

def get_drive_service(project_root: str) -> Resource:
    """
    Returns an authenticated Google Drive service object.

    Args:
        project_root (str): The absolute path to the project root directory.

    Returns:
        Resource: A Google Drive API service resource object ready to make requests.
    """
    creds = get_credentials(project_root)
    service = build("drive", "v3", credentials=creds)
    log.info("✅ Drive service initialized successfully.")
    return service
