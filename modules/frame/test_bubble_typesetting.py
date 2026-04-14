import cv2
import os
import sys
import numpy as np

# Inject modules path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from bubble_processor import Bubble

def test_typesetting():
    """Tests the typesetting of text inside a bubble mask."""
    bubble_proc = Bubble()
    
    # Path to sample bubble images
    body_path = os.path.join("modules", "frame", "bubble_frame", "elip_cleaned.jpg")
    full_path = os.path.join("modules", "frame", "bubble_frame", "elip_cleaned.jpg")
    
    abs_body_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", body_path))
    abs_full_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", full_path))

    if not os.path.exists(abs_body_path):
        print(f"Error: Sample bubble not found at {abs_body_path}")
        return
    
    # Extract tail from the full bubble image
    print(f"Extracting tail from: {abs_full_path}")
    full_img = cv2.imread(abs_full_path)
    _, tail_mask, _ = bubble_proc.decompose_bubble(full_img)

    text = "Hello! This is a test of the auto-typesetting system. It should fit comfortably inside the bubble without clipping.Hello! This is a test of the auto-typesetting system. It should fit comfortably inside the bubble without clipping. Hello! This is a test of the auto-typesetting system. It should fit comfortably inside the bubble without clipping. "
    
    print(f"Processing bubble body: {abs_body_path}")
    image = cv2.imread(abs_body_path)
    
    print("Reattaching tail at 120 degrees and typesetting...")
    result = bubble_proc.typeset_text(image, text, angle=120, tail_mask=tail_mask, padding_erosion=15)
    
    output_path = os.path.join("test_typeset_result.jpg")
    cv2.imwrite(output_path, result)
    print(f"Result saved to: {output_path}")

if __name__ == "__main__":
    test_typesetting()
