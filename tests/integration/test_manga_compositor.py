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
from modules.frame.manga_processor import create_manga_page_with_dialogue

class TestMangaCompositor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.join(settings.OUTPUT_DIR, "test_compositor_tmp")
        os.makedirs(cls.test_dir, exist_ok=True)
        
        # Create synthetic test panel images
        cls.img_paths = []
        for i in range(3):
            p = os.path.join(cls.test_dir, f"panel_{i}.png")
            img = np.zeros((400, 400, 3), dtype=np.uint8)
            img[:, :] = (50 * i, 100, 150)
            cv2.imwrite(p, img)
            cls.img_paths.append(p)

        cls.frame_dialogue_pairs = [
            {
                "keyframe_path": cls.img_paths[0],
                "timestamp": 2.0,
                "frame_index": 60,
                "speaker": "SPEAKER_01",
                "dialogue": "Hello world!"
            },
            {
                "keyframe_path": cls.img_paths[1],
                "timestamp": 8.0,
                "frame_index": 240,
                "speaker": "SPEAKER_02",
                "dialogue": "Welcome to Vid2Manga."
            },
            {
                "keyframe_path": cls.img_paths[2],
                "timestamp": 15.0,
                "frame_index": 450,
                "speaker": "SPEAKER_01",
                "dialogue": ""
            }
        ]

    @patch("modules.frame.manga_processor.get_segmenter")
    def test_create_manga_page_with_dialogue(self, mock_get_segmenter):
        mock_segmenter_inst = MagicMock()
        mock_segmenter_inst.segment.return_value = ([], [], [], [])
        mock_get_segmenter.return_value = mock_segmenter_inst

        page = create_manga_page_with_dialogue(
            frame_dialogue_pairs=self.frame_dialogue_pairs,
            stylize_style='c',
            width=800,
            height=1200,
            enable_bubbles=True,
            seed=42
        )

        self.assertIsNotNone(page)
        self.assertEqual(page.width, 800)
        self.assertEqual(page.height, 1200)

        out_file = os.path.join(self.test_dir, "composited_manga_page.png")
        page.save(out_file)
        self.assertTrue(os.path.exists(out_file))
        self.assertGreater(os.path.getsize(out_file), 0)

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
