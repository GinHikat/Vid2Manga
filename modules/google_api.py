'''
To use these functions, grant the "Editor" permission to the service account email on the target Google Sheet/ Google Drive and
                                                                            change the ID in the function parameter

"gg-service-agent@legalrag-471601.iam.gserviceaccount.com" 

Link to sheet: https://docs.google.com/spreadsheets/d/1mEZ94OrVd_5svkAkhqHuUEPilDddG5fobanDsw7B8xU/edit?gid=0#gid=0

Link to drive: https://drive.google.com/drive/folders/16dRxPz4tVDPScwuYOQ_U5opRdg96qW9W?usp=drive_link
'''
import io, sys, os
import gspread
import pandas as pd
from typing import List, Dict, Optional
from collections import defaultdict
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.cloud import storage

load_dotenv()

# Configuration from environment variables
GOOGLE_API_CREDS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
DRIVE_ID = os.getenv('GOOGLE_DRIVE_ID')

def get_creds(path=GOOGLE_API_CREDS):
    """Returns credentials from file path."""
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Google credentials not found at: {path}")
    return path

# --- Google Sheets ---
def gs_to_df(tab_name, sheet_id=SHEET_ID, creds_path=GOOGLE_API_CREDS):
    """Reads a Google Sheet tab into a DataFrame."""
    gc = gspread.service_account(filename=get_creds(creds_path))
    wks = gc.open_by_key(sheet_id).worksheet(tab_name)
    return pd.DataFrame(wks.get_all_records())

def write_df_to_gs(df, tab_name, sheet_id=SHEET_ID, creds_path=GOOGLE_API_CREDS):
    """Appends or creates a worksheet from a DataFrame."""
    gc = gspread.service_account(filename=get_creds(creds_path))
    sh = gc.open_by_key(sheet_id)
    try:
        wks = sh.worksheet(tab_name)
        wks.update(f"A{len(wks.get_all_values())+1}", df.values.tolist())
    except gspread.exceptions.WorksheetNotFound:
        wks = sh.add_worksheet(title=tab_name, rows=str(len(df)+1), cols=str(len(df.columns)))
        wks.update([df.columns.values.tolist()] + df.values.tolist())
    return f"Done: {tab_name}"

# --- Google Drive ---
def get_drive_service(creds_path=GOOGLE_API_CREDS):
    """Builds a Google Drive service object."""
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_file(get_creds(creds_path), scopes=scopes)
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(filepath, folder_name, creds_path=GOOGLE_API_CREDS):
    """Uploads a file to a named Google Drive folder."""
    service = get_drive_service(creds_path)
    # Finding folder ID (simplistic)
    q = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    folders = service.files().list(q=q, fields="files(id)").execute().get('files', [])
    if not folders: raise ValueError(f"Folder '{folder_name}' not found")
    
    meta = {'name': os.path.basename(filepath), 'parents': [folders[0]['id']]}
    mime = mimetypes.guess_type(filepath)[0] or 'application/octet-stream'
    media = MediaFileUpload(filepath, mimetype=mime, resumable=True)
    file = service.files().create(body=meta, media_body=media, fields='id').execute()
    return file.get('id')

# --- Google Cloud Storage ---
def get_gcs_client(creds_path=GOOGLE_API_CREDS):
    """Returns a GCS client object."""
    creds = service_account.Credentials.from_service_account_file(get_creds(creds_path))
    return storage.Client(credentials=creds, project=creds.project_id)

def upload_to_gcs(local_path, bucket_name, destination_blob=None, creds_path=GOOGLE_API_CREDS):
    """Uploads a file to GCS."""
    bucket = get_gcs_client(creds_path).bucket(bucket_name)
    blob = bucket.blob(destination_blob or os.path.basename(local_path))
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{blob.name}"

