import os
import cv2
import uuid
import numpy as np
from PIL import Image
from core.config import settings
from modules.frame.stylizer import stylize_a, stylize_b, stylize_c, cv2_to_pil
from modules.frame.layout_generator import generate_manga_layout, create_manga_page
from modules.frame.human_detector import PersonSegmenter

segmenter = PersonSegmenter()

def draw_masks(image_np, masks, color=(255, 0, 0), alpha=0.5):
    """Draws segmentation masks on image."""
    result = image_np.copy()
    for mask in masks:
        idx = mask > 0
        if len(idx.shape) == 2:
            result[idx] = (result[idx] * (1 - alpha) + np.array(color) * alpha).astype(np.uint8)
    return result

async def process_manga_generation(
    image_paths, width=1000, height=1400, num_frames=8, 
    seed=42, stylize_style='c', segment_human=False, show_mask=False
):
    """Orchestrates the full manga page generation pipeline."""
    processed_images = []
    
    for path in image_paths:
        stylizer_map = {'a': stylize_a, 'b': stylize_b, 'c': stylize_c}
        proc_cv2 = stylizer_map.get(stylize_style, stylize_c)(path)
            
        if proc_cv2 is None:
            img = cv2.imread(path)
            if img is not None: proc_cv2 = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else: continue

        if segment_human:
            try:
                _, _, masks, _ = segmenter.segment(path)
                if show_mask and masks:
                    proc_cv2 = draw_masks(proc_cv2, masks)
            except Exception as e:
                print(f"Segmentation error for {path}: {e}")

        processed_images.append(cv2_to_pil(proc_cv2))

    if not processed_images: raise ValueError("No images processed.")

    actual_num = num_frames if num_frames > 0 else len(processed_images)
    urls = []
    
    for i in range(0, len(processed_images), actual_num):
        chunk = processed_images[i:i + actual_num]
        while len(chunk) < actual_num:
            chunk.append(Image.new('RGB', (100, 100), "white"))

        frames = generate_manga_layout(width, height, actual_num, seed + i, 0.05, 8)
        page = create_manga_page(chunk, frames, width, height, "white")

        output_name = f"manga_{uuid.uuid4()}.png"
        page.save(os.path.join(settings.OUTPUT_DIR, output_name))
        urls.append(f"/output/{output_name}")
        
    return urls
