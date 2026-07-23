import os
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"
import cv2
try:
    cv2.setLogLevel(0)
except Exception:
    pass
import numpy as np
from fastapi import UploadFile, HTTPException
from core.config import settings
from modules.speech.process_audio import split_video_audio, speech2text
from modules.task_manager import update_task_status, update_task_error, update_task_result, TaskStatus

# --- Keyframe Extraction Helper Utilities ---

def _is_frame_clear(frame: np.ndarray, blur_threshold: float = 80.0, brightness_threshold: float = 40.0) -> tuple[bool, float]:
    """Checks if an in-memory frame image is sharp and illuminated sufficiently.

    Args:
        frame: OpenCV BGR image array.
        blur_threshold: Minimum variance of Laplacian for blur detection.
        brightness_threshold: Minimum mean grayscale value for brightness.

    Returns:
        tuple[bool, float]: (is_clear: bool, sharpness_score: float).
    """
    if frame is None:
        return False, 0.0
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    avg_brightness = float(np.mean(gray))
    if laplacian_var < blur_threshold or avg_brightness < brightness_threshold:
        return False, laplacian_var
    return True, laplacian_var

def _compute_hsv_diff(prev_frame: np.ndarray, curr_frame: np.ndarray) -> float:
    """Computes normalized HSV histogram distance between two frames to detect scene changes.

    Args:
        prev_frame: Previous OpenCV frame array.
        curr_frame: Current OpenCV frame array.

    Returns:
        float: Difference score in range [0.0, 1.0] where higher values indicate scene transitions.
    """
    if prev_frame is None or curr_frame is None:
        return 1.0
    prev_hsv = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2HSV)
    curr_hsv = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2HSV)
    hist_prev = cv2.calcHist([prev_hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
    hist_curr = cv2.calcHist([curr_hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
    cv2.normalize(hist_prev, hist_prev, 0, 1, cv2.NORM_MINMAX)
    cv2.normalize(hist_curr, hist_curr, 0, 1, cv2.NORM_MINMAX)
    correlation = cv2.compareHist(hist_prev, hist_curr, cv2.HISTCMP_CORREL)
    return max(0.0, float(1.0 - correlation))

class suppress_c_stderr:
    """Context manager that redirects C-level file descriptor 2 (stderr) to os.devnull."""
    def __enter__(self):
        try:
            self.null_fd = os.open(os.devnull, os.O_WRONLY)
            self.save_fd = os.dup(2)
            os.dup2(self.null_fd, 2)
        except Exception:
            self.save_fd = None
        return self

    def __exit__(self, *args):
        if hasattr(self, 'save_fd') and self.save_fd is not None:
            try:
                os.dup2(self.save_fd, 2)
                os.close(self.save_fd)
                os.close(self.null_fd)
            except Exception:
                pass

# --- Main Keyframe Extraction Function ---

def extract_keyframes(
    video_path: str,
    interval_sec: float = 5.0,
    output_dir: str = None,
    time_range: tuple = None,
    max_scene_gap_sec: float = 7.0,
    detect_scenes: bool = True,
    scene_threshold: float = 0.35,
    min_clarity: bool = True,
    blur_threshold: float = 80.0,
    detect_persons: bool = False
) -> list[dict]:
    """Extracts scene-aware, quality-validated keyframes across a video stream.

    Enforces a maximum safety gap constraint (max_scene_gap_sec = 7.0) to prevent dialogue
    accumulation and text overflow in downstream manga speech bubbles.

    Args:
        video_path: Path to input video file (absolute or relative to settings.INPUT_DIR).
        interval_sec: Default interval in seconds between extracted keyframes.
        output_dir: Output directory for keyframe images. Defaults to settings.OUTPUT_DIR/keyframes.
        time_range: Optional tuple (start_sec, end_sec) to constrain extraction window.
        max_scene_gap_sec: Maximum allowable time gap between consecutive keyframes (safety constraint).
        detect_scenes: Whether to trigger keyframes on HSV histogram scene changes.
        scene_threshold: Threshold difference for scene change detection (0.0 to 1.0).
        min_clarity: Whether to skip blurry or dark candidate frames.
        blur_threshold: Laplacian variance threshold for sharpness filtering.
        detect_persons: Whether to run PersonSegmenter to score human subject presence.

    Returns:
        list[dict]: List of frame metadata dictionaries containing path, timestamp, frame_index, etc.
    """
    if not os.path.isabs(video_path):
        potential_path = os.path.join(settings.INPUT_DIR, video_path)
        if os.path.exists(potential_path):
            video_path = potential_path

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    if output_dir is None:
        output_dir = os.path.join(settings.OUTPUT_DIR, "keyframes")

    os.makedirs(output_dir, exist_ok=True)

    with suppress_c_stderr():
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration_sec = total_video_frames / fps if total_video_frames > 0 else 0.0

        if time_range:
            start_sec, end_sec = time_range
            start_frame_idx = max(0, int(start_sec * fps))
            end_frame_idx = min(total_video_frames - 1, int(end_sec * fps)) if total_video_frames > 0 else int(end_sec * fps)
        else:
            start_frame_idx = 0
            end_frame_idx = total_video_frames - 1 if total_video_frames > 0 else 99999999

        # Fine sampling step: check candidate frames every ~0.5 seconds
        sample_step = max(1, int(fps * 0.5))

        person_segmenter = None

        base_name = os.path.splitext(os.path.basename(video_path))[0]
        extracted_frames = []
        
        last_saved_timestamp = -999.0
        prev_frame_bgr = None
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame_idx)
        curr_frame_idx = start_frame_idx

        while curr_frame_idx <= end_frame_idx:
            cap.set(cv2.CAP_PROP_POS_FRAMES, curr_frame_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            timestamp = round(curr_frame_idx / fps, 2)
            time_since_last = timestamp - last_saved_timestamp

            is_clear, sharpness = _is_frame_clear(frame, blur_threshold=blur_threshold)
            hsv_diff = _compute_hsv_diff(prev_frame_bgr, frame) if prev_frame_bgr is not None else 1.0

            # Evaluate extraction triggers
            trigger_reason = None

            if len(extracted_frames) == 0:
                trigger_reason = "initial"
            elif time_since_last >= max_scene_gap_sec:
                trigger_reason = "safety_gap_7s"
            elif detect_scenes and hsv_diff >= scene_threshold:
                trigger_reason = "scene_change"
            elif time_since_last >= interval_sec:
                trigger_reason = "interval"

            # Apply clarity filtering unless forced by 7-second safety gap or initial frame
            if trigger_reason:
                if min_clarity and not is_clear and trigger_reason not in ["safety_gap_7s", "initial"]:
                    prev_frame_bgr = frame.copy()
                    curr_frame_idx += sample_step
                    continue

                has_person = False

                filename = f"{base_name}_frame_{int(timestamp):04d}s.png"
                save_path = os.path.join(output_dir, filename)
                cv2.imwrite(save_path, frame)

                extracted_frames.append({
                    "path": os.path.abspath(save_path),
                    "timestamp": timestamp,
                    "frame_index": curr_frame_idx,
                    "sharpness_score": round(sharpness, 2),
                    "hsv_diff": round(hsv_diff, 3),
                    "has_person": has_person,
                    "trigger": trigger_reason
                })

                last_saved_timestamp = timestamp
                prev_frame_bgr = frame.copy()

            curr_frame_idx += sample_step

        cap.release()

    return extracted_frames

def split_vid(video_path: str, partition_length: float = 20.0, output_dir: str = None) -> list[str]:
    """Splits a video file into multiple partitioned video segments of specified duration.

    Args:
        video_path: Path to the input video file (absolute or relative to settings.INPUT_DIR).
        partition_length: Duration of each video partition in seconds.
        output_dir: Target directory for storing partitions. Defaults to settings.OUTPUT_DIR/video_chunks.

    Returns:
        list[str]: List of paths to the generated video partition files.
    """
    if not os.path.isabs(video_path):
        potential_path = os.path.join(settings.INPUT_DIR, video_path)
        if os.path.exists(potential_path):
            video_path = potential_path

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    if output_dir is None:
        output_dir = os.path.join(settings.OUTPUT_DIR, "video_chunks")

    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_pattern = os.path.join(output_dir, f"{base_name}_part_%03d.mp4")

    # --- FFmpeg Video Partitioning ---
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-c", "copy",
        "-map", "0",
        "-segment_time", str(partition_length),
        "-f", "segment",
        "-reset_timestamps", "1",
        output_pattern
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        cmd_reencode = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-segment_time", str(partition_length),
            "-f", "segment",
            "-reset_timestamps", "1",
            output_pattern
        ]
        result_reencode = subprocess.run(cmd_reencode, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result_reencode.returncode != 0:
            raise RuntimeError(f"FFmpeg partitioning failed: {result_reencode.stderr}")

    generated_partitions = sorted([
        os.path.abspath(os.path.join(output_dir, f))
        for f in os.listdir(output_dir)
        if f.startswith(f"{base_name}_part_") and f.endswith(".mp4")
    ])

    return generated_partitions

async def process_video(file: UploadFile) -> tuple[str, str, str | None]:
    """Processes video: saves, splits audio/video, and transcribes."""
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a video.")
    
    try:
        file_location = os.path.join(settings.INPUT_DIR, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        audio_path, video_path = split_video_audio(file_location)
        
        # Relative URLs for frontend
        audio_rel = os.path.relpath(audio_path, settings.OUTPUT_DIR).replace("\\", "/")
        video_rel = os.path.relpath(video_path, settings.OUTPUT_DIR).replace("\\", "/")
        
        res = speech2text(os.path.basename(audio_path))
        return f"/output/{video_rel}", f"/output/{audio_rel}", res.get("text", "")

    except Exception as e:
        print(f"Error in process_video: {e}\n{traceback.format_exc()}")
        if hasattr(e, 'stderr'): print(f"FFmpeg stderr: {e.stderr}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

async def process_video_task(task_id: str, file_location: str, original_filename: str, language: str = "en"):
    """Background task for video processing and end-to-end manga volume generation."""
    try:
        update_task_status(task_id, TaskStatus.PROCESSING)
        
        from modules.task_manager import update_task_progress
        from modules.frame.end_to_end_vid2manga import process_video_to_manga_volume

        def progress_cb(msg):
            update_task_progress(task_id, msg)

        manga_res = process_video_to_manga_volume(file_location, language=language, progress_callback=progress_cb)

        from modules.mlops.gdrive_storage import is_gdrive_available, upload_file_to_drive
        if is_gdrive_available():
            try:
                base_name = os.path.splitext(os.path.basename(file_location))[0]
                if "pdf_path" in manga_res and os.path.exists(manga_res["pdf_path"]):
                    gdrive_res = upload_file_to_drive(manga_res["pdf_path"], drive_filename=f"{base_name}_manga.pdf", subfolder_name="output")
                    manga_res["pdf_url"] = gdrive_res["web_view_link"]
                page_gdrive_urls = []
                for i, page_rel in enumerate(manga_res.get("manga_urls", [])):
                    page_filename = os.path.basename(page_rel)
                    local_page_path = os.path.join(settings.OUTPUT_DIR, page_filename)
                    if os.path.exists(local_page_path):
                        img_res = upload_file_to_drive(local_page_path, drive_filename=page_filename, subfolder_name="output")
                        page_gdrive_urls.append(img_res["direct_image_url"])
                    else:
                        page_gdrive_urls.append(page_rel)
                if page_gdrive_urls:
                    manga_res["manga_urls"] = page_gdrive_urls
            except Exception as e:
                print(f"Warning: Google Drive upload failed in process_video_task: {e}")

        audio_path, video_path = split_video_audio(file_location)
        audio_rel = os.path.relpath(audio_path, settings.OUTPUT_DIR).replace("\\", "/")
        video_rel = os.path.relpath(video_path, settings.OUTPUT_DIR).replace("\\", "/")

        update_task_result(task_id, {
            "video_url": f"/output/{video_rel}",
            "audio_url": f"/output/{audio_rel}",
            "pdf_url": manga_res.get("pdf_url"),
            "manga_urls": manga_res.get("manga_urls", []),
            "total_pages": manga_res.get("total_pages", 0),
            "total_keyframes": manga_res.get("total_keyframes", 0),
            "text": manga_res.get("text", ""),
            "segments": manga_res.get("segments", [])
        })
    except Exception as e:
        stderr_msg = f" | FFmpeg stderr: {e.stderr}" if hasattr(e, 'stderr') else ""
        print(f"Error task {task_id}: {e}{stderr_msg}\n{traceback.format_exc()}")
        update_task_error(task_id, f"Processing failed: {str(e)}{stderr_msg}")
