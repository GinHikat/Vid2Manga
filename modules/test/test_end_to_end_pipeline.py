import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure root directory and App/backend are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "App", "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

import cv2
import numpy as np
from core.config import settings

def create_synthetic_e2e_video(video_path: str, duration_sec: float = 15.0, fps: float = 30.0):
    """Generates a synthetic test video for end-to-end pipeline testing."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    width, height = 640, 480
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

    total_frames = int(duration_sec * fps)
    for i in range(total_frames):
        t = i / fps
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        if t < 5.0:
            frame[:, :] = (0, 0, 180)
        elif t < 10.0:
            frame[:, :] = (0, 180, 0)
        else:
            frame[:, :] = (180, 0, 0)
        out.write(frame)

    out.release()

class TestEndToEndPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.join(settings.OUTPUT_DIR, "test_e2e_tmp")
        os.makedirs(cls.test_dir, exist_ok=True)
        cls.video_path = os.path.join(cls.test_dir, "synthetic_e2e.mp4")
        create_synthetic_e2e_video(cls.video_path, duration_sec=15.0, fps=30.0)

    @patch("modules.speech.process_audio.split_video_audio")
    @patch("modules.speech.process_audio.speech2text")
    @patch("modules.frame.end_to_end_vid2manga.split_video_audio")
    @patch("modules.frame.end_to_end_vid2manga.speech2text")
    @patch("modules.frame.human_detector.PersonSegmenter")
    def test_process_video_to_manga_volume(self, mock_segmenter_cls, mock_stt2, mock_split2, mock_stt1, mock_split1):
        mock_split1.return_value = ("/tmp/mock_audio.wav", self.video_path)
        mock_split2.return_value = ("/tmp/mock_audio.wav", self.video_path)
        mock_stt1.return_value = {
            "text": "Hello world! Welcome to Vid2Manga pipeline test.",
            "segments": [
                {"start": 1.0, "end": 4.0, "speaker": "SPEAKER_01", "text": "Hello world!"},
                {"start": 6.0, "end": 9.0, "speaker": "SPEAKER_02", "text": "Welcome to Vid2Manga pipeline test."}
            ]
        }
        mock_stt2.return_value = mock_stt1.return_value

        # Mock PersonSegmenter instance
        mock_inst = MagicMock()
        mock_inst.segment.return_value = ([], [], [], [])
        mock_segmenter_cls.return_value = mock_inst

        from modules.frame.end_to_end_vid2manga import process_video_to_manga_volume

        result = process_video_to_manga_volume(
            video_path=self.video_path,
            num_frames_per_page=5,
            stylize_style="c",
            output_pdf_name="test_e2e_volume.pdf"
        )

        self.assertIn("pdf_path", result)
        self.assertIn("pdf_url", result)
        self.assertIn("manga_urls", result)
        self.assertGreater(result["total_pages"], 0)
        self.assertGreater(result["total_keyframes"], 0)
        self.assertTrue(os.path.exists(result["pdf_path"]))
        self.assertGreater(os.path.getsize(result["pdf_path"]), 0)

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
