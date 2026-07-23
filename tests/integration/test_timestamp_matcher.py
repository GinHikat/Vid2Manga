import os
import sys
import unittest

# Ensure root directory and App/backend are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "App", "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from modules.frame.timestamp_matcher import (
    match_keyframes_with_dialogue,
    find_best_keyframe_for_segment
)

class TestTimestampMatcher(unittest.TestCase):

    def setUp(self):
        self.sample_keyframes = [
            {"path": "/tmp/frame_0s.png", "timestamp": 2.0, "frame_index": 60},
            {"path": "/tmp/frame_8s.png", "timestamp": 8.0, "frame_index": 240},
            {"path": "/tmp/frame_15s.png", "timestamp": 15.0, "frame_index": 450}
        ]

        self.sample_speech_segments = [
            {"start": 1.0, "end": 4.0, "speaker": "SPEAKER_01", "text": "Hello there!"},
            {"start": 7.0, "end": 10.0, "speaker": "SPEAKER_02", "text": "Good morning."},
            {"start": 14.0, "end": 17.0, "speaker": "SPEAKER_01", "text": "See you later."}
        ]

    def test_match_keyframes_with_dialogue(self):
        pairs = match_keyframes_with_dialogue(self.sample_keyframes, self.sample_speech_segments)
        
        self.assertEqual(len(pairs), 3)

        # Panel 1 (t = 2.0s) should match SPEAKER_01 "Hello there!"
        self.assertEqual(pairs[0]["speaker"], "SPEAKER_01")
        self.assertEqual(pairs[0]["dialogue"], "Hello there!")

        # Panel 2 (t = 8.0s) should match SPEAKER_02 "Good morning."
        self.assertEqual(pairs[1]["speaker"], "SPEAKER_02")
        self.assertEqual(pairs[1]["dialogue"], "Good morning.")

        # Panel 3 (t = 15.0s) should match SPEAKER_01 "See you later."
        self.assertEqual(pairs[2]["speaker"], "SPEAKER_01")
        self.assertEqual(pairs[2]["dialogue"], "See you later.")

    def test_empty_speech_segments(self):
        pairs = match_keyframes_with_dialogue(self.sample_keyframes, [])
        self.assertEqual(len(pairs), 3)
        for pair in pairs:
            self.assertEqual(pair["dialogue"], "")
            self.assertEqual(pair["speaker"], "Unknown Speaker")

    def test_find_best_keyframe_for_segment(self):
        segment = {"start": 7.5, "end": 9.5, "speaker": "SPEAKER_02", "text": "Test speech"}
        best_kf = find_best_keyframe_for_segment(segment, self.sample_keyframes)
        self.assertEqual(best_kf["timestamp"], 8.0)

if __name__ == "__main__":
    unittest.main()
