import os
import sys
import time

# Ensure project root & backend are in python path
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('App/backend'))

from dotenv import load_dotenv
load_dotenv()

def run_gdrive_celery_pipeline_test():
    """Integration test script to test the full Google Drive + Celery pipeline locally."""
    print("=" * 70)
    print("🚀 STARTING END-TO-END GOOGLE DRIVE + CELERY PIPELINE TEST")
    print("=" * 70)

    from modules.mlops.gdrive_storage import is_gdrive_available, upload_file_to_drive
    from modules.mlops.tasks import process_video_celery_task
    from modules.mlops.celery_app import is_celery_worker_active

    # 1. Verify environment & setup
    test_video_path = os.path.abspath("data/video/vid1.mp4")
    if not os.path.exists(test_video_path):
        raise FileNotFoundError(f"Test video file not found at: {test_video_path}")
    print(f"✅ Found input test video: {test_video_path}")

    # 2. Check Google Drive connectivity
    print("\n🔍 Step 1: Checking Google Drive API availability...")
    if not is_gdrive_available():
        print("❌ Error: Google Drive API is not available or credentials missing.")
        return
    print("✅ Google Drive API is online & accessible.")

    # 3. Check Celery worker status
    print("\n🔍 Step 2: Checking local Celery worker status...")
    if not is_celery_worker_active(timeout=2.0):
        print("❌ Error: No local Celery worker detected.")
        print("   Please start your local Celery worker in another terminal:")
        print("   celery -A modules.mlops.celery_app worker --loglevel=info --pool=solo")
        return
    print("✅ Active Celery worker detected on Redis broker.")

    # 4. Upload input video to Google Drive input/ subfolder
    filename = os.path.basename(test_video_path)
    print(f"\n📤 Step 3: Uploading {filename} to Google Drive input/ subfolder...")
    upload_res = upload_file_to_drive(test_video_path, drive_filename=filename, subfolder_name="input")
    gdrive_file_id = upload_res["id"]
    gdrive_param = f"gdrive:{gdrive_file_id}"
    print(f"✅ Upload successful! File ID: {gdrive_file_id}")
    print(f"   Parameter string: {gdrive_param}")

    # 5. Dispatch task to Celery
    print(f"\n⚡ Step 4: Dispatching task to Celery queue (Task Param: {gdrive_param})...")
    async_result = process_video_celery_task.delay(
        video_path=gdrive_param,
        filename=filename,
        num_frames_per_page=7,
        stylize_style="c",
        language="en"
    )
    task_id = async_result.id
    print(f"✅ Celery Task Dispatched! Task ID: {task_id}")

    # 6. Poll task completion
    print("\n⏳ Step 5: Waiting for Celery worker to download from Drive & process ML pipeline...")
    start_time = time.time()
    while not async_result.ready():
        time.sleep(2)
        elapsed = int(time.time() - start_time)
        print(f"   [+{elapsed}s] Processing... state: {async_result.state}")

    if async_result.failed():
        print("\n❌ Task Failed!")
        print(f"Error: {async_result.result}")
        return

    result = async_result.get()
    print("=" * 70)
    print("🎉 FULL PIPELINE SUCCESSFUL!")
    print("=" * 70)
    print(f"📄 Output PDF URL: {result.get('pdf_url')}")
    print(f"🖼️ Manga Page PNG URLs ({len(result.get('manga_urls', []))} pages):")
    for i, page_url in enumerate(result.get('manga_urls', []), 1):
        print(f"   Page {i}: {page_url}")
    print(f"📊 Total Keyframes Extracted: {result.get('total_keyframes')}")
    print(f"💬 Speech Segments Found: {len(result.get('segments', []))}")
    print("=" * 70)

if __name__ == "__main__":
    run_gdrive_celery_pipeline_test()
