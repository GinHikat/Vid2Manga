import os
import sys

# Ensure root directory and App/backend are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "App", "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from core.config import settings
from modules.frame.end_to_end_vid2manga import process_video_to_manga_volume

def main():
    candidate_paths = [
        os.path.join(settings.ROOT_DIR, "data", "video", "sample_vid.mp4"),
        os.path.join(settings.INPUT_DIR, "sample_vid.mp4"),
        os.path.join(settings.DATA_DIR, "video", "sample_vid.mp4")
    ]
    video_path = next((p for p in candidate_paths if os.path.exists(p)), None)
    if not video_path:
        print(f"Error: Sample video not found in candidate paths.")
        return

    print("=" * 80)
    print(f"Running Full Video-to-Manga Pipeline on: {video_path}")
    print("=" * 80)

    result = process_video_to_manga_volume(
        video_path=video_path,
        num_frames_per_page=7,
        stylize_style="c",          language="en"
    )

    print("\n" + "=" * 80)
    print("PIPELINE EXECUTION COMPLETE!")
    print(f"PDF Output Path   : {result['pdf_path']}")
    print(f"PDF Output URL    : {result['pdf_url']}")
    print(f"Total Pages       : {result['total_pages']}")
    print(f"Total Keyframes   : {result['total_keyframes']}")
    print(f"Manga Page URLs   :")
    for url in result["manga_urls"]:
        print(f"  - {url}")
    print("=" * 80)

if __name__ == "__main__":
    main()
