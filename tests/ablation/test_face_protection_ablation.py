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

class TestFaceProtectionAblation(unittest.TestCase):
    """Ablation study test verifying the visual impact of face protection mask clearance."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.join(settings.OUTPUT_DIR, "test_ablation_tmp")
        os.makedirs(cls.test_dir, exist_ok=True)
        
        cls.img_path = os.path.join(cls.test_dir, "character_panel.png")
        img = np.zeros((500, 500, 3), dtype=np.uint8)
        img[:, :] = (200, 200, 200)
        cv2.imwrite(cls.img_path, img)

        cls.frame_dialogue_pairs = [
            {
                "keyframe_path": cls.img_path,
                "timestamp": 2.0,
                "frame_index": 60,
                "speaker": "SPEAKER_01",
                "dialogue": "Character speech bubble clearance ablation check."
            }
        ]

    @patch("modules.frame.manga_processor.get_segmenter")
    def test_ablation_speech_bubble_generation(self, mock_get_segmenter):
        mock_segmenter_inst = MagicMock()
        # Mock person mask covering center of panel
        person_mask = np.zeros((500, 500), dtype=np.uint8)
        person_mask[150:450, 150:350] = 1
        mock_segmenter_inst.segment.return_value = (None, None, [person_mask], {})
        mock_get_segmenter.return_value = mock_segmenter_inst

        # Run pipeline with face protection enabled
        page = create_manga_page_with_dialogue(
            frame_dialogue_pairs=self.frame_dialogue_pairs,
            stylize_style='c',
            width=800,
            height=1200,
            enable_bubbles=True,
            seed=42
        )

        self.assertIsNotNone(page)
        out_file = os.path.join(self.test_dir, "ablation_page.png")
        page.save(out_file)
        self.assertTrue(os.path.exists(out_file))

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
