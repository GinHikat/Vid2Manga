import os
import sys
from modules.mlops.celery_app import celery_app
from modules.frame.end_to_end_vid2manga import process_video_to_manga_volume

if celery_app is not None:
    @celery_app.task(bind=True, name="tasks.process_video_celery_task")
    def process_video_celery_task(self, video_path: str, num_frames_per_page: int = 7, stylize_style: str = "c", language: str = "en"):
        """Celery background worker task for processing video to manga volume PDF."""
        def progress_callback(step_msg: str):
            self.update_state(
                state="PROGRESS",
                meta={
                    "progress_msg": step_msg,
                    "status": "processing"
                }
            )

        result = process_video_to_manga_volume(
            video_path=video_path,
            num_frames_per_page=num_frames_per_page,
            stylize_style=stylize_style,
            language=language,
            progress_callback=progress_callback
        )

        return result
else:
    process_video_celery_task = None
