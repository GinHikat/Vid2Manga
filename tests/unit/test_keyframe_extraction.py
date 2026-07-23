import os
import sys
import unittest
import cv2
import numpy as np

# Ensure root directory and App/backend are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "App", "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from core.config import settings
from modules.frame.video_processor import extract_keyframes

def create_synthetic_test_video(video_path: str, duration_sec: float = 18.0, fps: float = 30.0):
    """Generates a synthetic test video with scene changes and colored shapes."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    width, height = 640, 480
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

    total_frames = int(duration_sec * fps)
    for i in range(total_frames):
        t = i / fps
        if t < 5.0:
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :] = (0, 0, 200)
        elif t < 12.0:
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :] = (0, 200, 0)
            cv2.rectangle(frame, (100 + int(t * 10), 100), (250 + int(t * 10), 250), (250, 0, 0), -1)
        else:
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :] = (200, 0, 0)

        out.write(frame)

    out.release()

class TestKeyframeExtraction(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.join(settings.OUTPUT_DIR, "test_keyframes_unit_tmp")
        os.makedirs(cls.test_dir, exist_ok=True)
        cls.video_path = os.path.join(cls.test_dir, "synthetic_test.mp4")
        create_synthetic_test_video(cls.video_path, duration_sec=18.0, fps=30.0)

    def test_extract_keyframes_scene_and_safety_gap(self):
        output_dir = os.path.join(self.test_dir, "output")
        keyframes = extract_keyframes(
            video_path=self.video_path,
            output_dir=output_dir,
            max_scene_gap_sec=7.0,
            detect_scenes=True,
            scene_threshold=0.3
        )

        self.assertGreater(len(keyframes), 0)
        
        # Verify metadata payload
        for kf in keyframes:
            self.assertIn("path", kf)
            self.assertIn("timestamp", kf)
            self.assertIn("frame_index", kf)
            self.assertIn("sharpness_score", kf)
            self.assertIn("trigger", kf)
            self.assertTrue(os.path.exists(kf["path"]))

        # Verify 7-second max scene gap constraint
        timestamps = [kf["timestamp"] for kf in keyframes]
        for i in range(1, len(timestamps)):
            gap = timestamps[i] - timestamps[i - 1]
            self.assertLessEqual(gap, 7.5, f"Gap between keyframe {i-1} and {i} exceeded 7s limit: {gap}s")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            try:
                import shutil
                shutil.rmtree(cls.test_dir)
            except Exception:
                pass

if __name__ == "__main__":
    unittest.main()
