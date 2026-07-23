import io
import os
import sys
import mimetypes
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Ensure project root is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "App", "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from core.config import settings

def resolve_credentials_path() -> Optional[str]:
    """Resolves absolute path for GOOGLE_APPLICATION_CREDENTIALS or secrets/ggsheet_credentials.json."""
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        if os.path.isabs(creds_path) and os.path.exists(creds_path):
            return creds_path
        rel_path = os.path.join(settings.ROOT_DIR, creds_path)
        if os.path.exists(rel_path):
            return rel_path

    # Check standard secrets fallback paths (including Render /etc/secrets location)
    for candidate in [
        "/etc/secrets/ggsheet_credentials.json",
        os.path.join(settings.ROOT_DIR, "ggsheet_credentials.json"),
        os.path.join(settings.ROOT_DIR, "secrets", "ggsheet_credentials.json")
    ]:
        if os.path.exists(candidate):
            return candidate

    return None

def get_drive_service(creds_path: Optional[str] = None, scopes: Optional[List[str]] = None):
    """Authenticate and return a Google Drive API service object."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    if creds_path is None:
        creds_path = resolve_credentials_path()

    if not creds_path or not os.path.exists(creds_path):
        raise FileNotFoundError(f"Google Drive service account credentials file not found at: {creds_path}")

    if scopes is None:
        scopes = ['https://www.googleapis.com/auth/drive']

    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
    return build('drive', 'v3', credentials=creds)

def is_gdrive_available() -> bool:
    """Helper function to check if Google Drive API is configured and accessible."""
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID") or getattr(settings, "GOOGLE_DRIVE_FOLDER_ID", None)
    if not folder_id:
        return False
    try:
        creds_path = resolve_credentials_path()
        if not creds_path:
            return False
        service = get_drive_service(creds_path)
        # Test Drive API connection by fetching folder metadata
        service.files().get(fileId=folder_id, fields="id, name", supportsAllDrives=True).execute()
        return True
    except Exception as e:
        print(f"is_gdrive_available check failed: {e}")
        return False

def get_or_create_drive_subfolder(subfolder_name: str, parent_folder_id: Optional[str] = None) -> str:
    """Gets existing or creates a new subfolder (e.g. 'input' or 'output') inside parent Google Drive folder."""
    if parent_folder_id is None:
        parent_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID") or getattr(settings, "GOOGLE_DRIVE_FOLDER_ID", "")

    if not parent_folder_id:
        return ""

    try:
        service = get_drive_service()
        query = f"'{parent_folder_id}' in parents and name = '{subfolder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = service.files().list(q=query, fields="files(id, name)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        files = res.get("files", [])

        if files:
            return files[0]["id"]

        folder_metadata = {
            'name': subfolder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        created_folder = service.files().create(body=folder_metadata, fields='id', supportsAllDrives=True).execute()
        return created_folder.get('id')
    except Exception as e:
        print(f"Warning: Failed to get/create Google Drive subfolder '{subfolder_name}': {e}")
        return parent_folder_id

def upload_file_to_drive(
    file_path: str,
    folder_id: Optional[str] = None,
    drive_filename: Optional[str] = None,
    subfolder_name: Optional[str] = None,
    make_public: bool = True
) -> Dict[str, str]:
    """Uploads a local file to Google Drive folder using MediaFileUpload.

    Args:
        file_path: Path to local file to upload.
        folder_id: Target Google Drive folder ID. Defaults to GOOGLE_DRIVE_FOLDER_ID env var.
        drive_filename: Custom filename on Google Drive. Defaults to local filename.
        subfolder_name: Optional subfolder ('input' or 'output') inside target folder.
        make_public: If True, sets public viewer permission for web sharing.

    Returns:
        Dict with 'id', 'name', 'web_view_link', and 'web_content_link'.
    """
    from googleapiclient.http import MediaFileUpload

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File to upload not found: {file_path}")

    if subfolder_name:
        folder_id = get_or_create_drive_subfolder(subfolder_name, parent_folder_id=folder_id)

    if folder_id is None or folder_id == "":
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID") or getattr(settings, "GOOGLE_DRIVE_FOLDER_ID", "")

    if not drive_filename:
        drive_filename = os.path.basename(file_path)

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = "application/octet-stream"

    service = get_drive_service()
    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

    # Check if a file with the exact same name already exists in target folder
    existing_file_id = None
    if folder_id:
        try:
            query = f"'{folder_id}' in parents and name = '{drive_filename}' and trashed = false"
            res = service.files().list(q=query, fields="files(id, name)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
            existing_files = res.get("files", [])
            if existing_files:
                existing_file_id = existing_files[0]["id"]
        except Exception as e:
            print(f"Warning: Failed checking existing file in Drive: {e}")

    if existing_file_id:
        # Overwrite/update existing file content instead of creating duplicates
        uploaded_file = service.files().update(
            fileId=existing_file_id,
            media_body=media,
            fields='id, name, webViewLink, webContentLink',
            supportsAllDrives=True
        ).execute()
    else:
        # Create new file if it doesn't exist
        file_metadata = {'name': drive_filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, webContentLink',
            supportsAllDrives=True
        ).execute()

    file_id = uploaded_file.get('id')

    if make_public and file_id:
        try:
            permission = {'type': 'anyone', 'role': 'reader'}
            service.permissions().create(fileId=file_id, body=permission, supportsAllDrives=True).execute()
        except Exception as e:
            print(f"Warning: Failed to set public permission on Google Drive file {file_id}: {e}")

    return {
        'id': file_id,
        'name': uploaded_file.get('name'),
        'web_view_link': uploaded_file.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view"),
        'web_content_link': uploaded_file.get('webContentLink', f"https://drive.google.com/uc?id={file_id}&export=download")
    }

def download_file_from_drive(file_id: str, destination_path: str) -> str:
    """Downloads a file from Google Drive to local destination path using MediaIoBaseDownload.

    Args:
        file_id: Google Drive file ID.
        destination_path: Local path where the file should be saved.

    Returns:
        Absolute path to the downloaded file.
    """
    from googleapiclient.http import MediaIoBaseDownload

    os.makedirs(os.path.dirname(os.path.abspath(destination_path)), exist_ok=True)
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    
    with io.FileIO(destination_path, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

    return os.path.abspath(destination_path)
