import os
import sys
from modules.mlops.celery_app import celery_app
from modules.frame.end_to_end_vid2manga import process_video_to_manga_volume

if celery_app is not None:
    @celery_app.task(bind=True, name="tasks.process_video_celery_task")
    def process_video_celery_task(self, video_path: str, filename: str = None, num_frames_per_page: int = 7, stylize_style: str = "c", language: str = "en"):
        """Celery background worker task for processing video to manga volume PDF."""
        def progress_callback(step_msg: str):
            self.update_state(
                state="PROGRESS",
                meta={
                    "progress_msg": step_msg,
                    "status": "processing"
                }
            )

        # Check if video_path is a Google Drive file ID or cloud path
        from modules.mlops.gdrive_storage import is_gdrive_available, download_file_from_drive, upload_file_to_drive, get_drive_file_id_by_name
        from core.config import settings

        local_video_path = video_path

        if video_path.startswith("gdrive:"):
            drive_file_id = video_path.replace("gdrive:", "")
            target_filename = filename if filename else f"video_{drive_file_id[:8]}.mp4"
            local_video_path = os.path.join(settings.INPUT_DIR, target_filename)
            if not os.path.exists(local_video_path):
                progress_callback(f"[0/5] Downloading video from Google Drive (ID: {drive_file_id[:8]}...)...")
                download_file_from_drive(drive_file_id, local_video_path)
        else:
            target_filename = filename if filename else os.path.basename(video_path)
            local_video_path = os.path.join(settings.INPUT_DIR, target_filename)
            if not os.path.exists(local_video_path) and is_gdrive_available():
                progress_callback(f"[0/5] Looking up {target_filename} in Google Drive input folder...")
                g_id = get_drive_file_id_by_name(target_filename, subfolder_name="input")
                if g_id:
                    download_file_from_drive(g_id, local_video_path)

        result = process_video_to_manga_volume(
            video_path=local_video_path,
            num_frames_per_page=num_frames_per_page,
            stylize_style=stylize_style,
            language=language,
            progress_callback=progress_callback
        )

        # Upload final PDF volume to Google Drive if available
        if is_gdrive_available() and "pdf_path" in result and os.path.exists(result["pdf_path"]):
            try:
                base_name = os.path.splitext(os.path.basename(local_video_path))[0]
                pdf_drive_name = f"{base_name}_manga.pdf"
                progress_callback(f"[5/5] Uploading final PDF volume ({pdf_drive_name}) to Google Drive...")
                gdrive_res = upload_file_to_drive(result["pdf_path"], drive_filename=pdf_drive_name, subfolder_name="output")
                result["gdrive_pdf_id"] = gdrive_res["id"]
                result["gdrive_web_view_link"] = gdrive_res["web_view_link"]
                result["gdrive_web_content_link"] = gdrive_res["web_content_link"]
                result["pdf_url"] = gdrive_res["web_view_link"]
            except Exception as e:
                print(f"Warning: Google Drive upload failed: {e}")

        return result
else:
    process_video_celery_task = None
