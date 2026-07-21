import os
import shutil
import subprocess
import traceback
import cv2
from fastapi import UploadFile, HTTPException
from core.config import settings
from modules.speech.process_audio import split_video_audio, speech2text
from modules.task_manager import update_task_status, update_task_error, update_task_result, TaskStatus

def extract_keyframes(video_path: str, interval_sec: float = 5.0, output_dir: str = None) -> list[dict]:
    """Extracts keyframe images at fixed time intervals (e.g., every 5 seconds).

    Args:
        video_path: Path to input video file (absolute or relative to settings.INPUT_DIR).
        interval_sec: Interval in seconds between extracted keyframes.
        output_dir: Output directory for keyframe images. Defaults to settings.OUTPUT_DIR/keyframes.

    Returns:
        list[dict]: List of frame metadata dicts with 'path', 'timestamp', and 'frame_index'.
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

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    frame_step = max(1, int(fps * interval_sec))
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    
    extracted_frames = []
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_step == 0:
            timestamp = round(frame_count / fps, 2)
            filename = f"{base_name}_frame_{int(timestamp):04d}s.png"
            save_path = os.path.join(output_dir, filename)
            cv2.imwrite(save_path, frame)
            
            extracted_frames.append({
                "path": os.path.abspath(save_path),
                "timestamp": timestamp,
                "frame_index": frame_count
            })

        frame_count += 1

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
    """Background task for video processing."""
    try:
        update_task_status(task_id, TaskStatus.PROCESSING)
        audio_path, video_path = split_video_audio(file_location)
        
        audio_rel = os.path.relpath(audio_path, settings.OUTPUT_DIR).replace("\\", "/")
        video_rel = os.path.relpath(video_path, settings.OUTPUT_DIR).replace("\\", "/")
        
        res = speech2text(os.path.basename(audio_path), language=language)
        
        update_task_result(task_id, {
            "video_url": f"/output/{video_rel}",
            "audio_url": f"/output/{audio_rel}",
            "text": res.get("text", ""),
            "segments": res.get("segments", [])
        })
    except Exception as e:
        stderr_msg = f" | FFmpeg stderr: {e.stderr}" if hasattr(e, 'stderr') else ""
        print(f"Error task {task_id}: {e}{stderr_msg}\n{traceback.format_exc()}")
        update_task_error(task_id, f"Processing failed: {str(e)}{stderr_msg}")
