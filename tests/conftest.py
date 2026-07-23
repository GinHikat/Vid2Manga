import os
import sys
import pytest
import numpy as np
import cv2

# Ensure project root and App/backend are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_dir = os.path.join(root_dir, "App", "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from core.config import settings

@pytest.fixture(scope="session")
def synthetic_video_path(tmp_path_factory):
    """Pytest fixture generating a 15s synthetic test video file."""
    fn = tmp_path_factory.mktemp("media") / "synthetic_test.mp4"
    video_path = str(fn)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    width, height = 640, 480
    fps = 30.0
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

    total_frames = int(15.0 * fps)
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
    return video_path
