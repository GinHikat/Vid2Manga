import os
import sys
import cv2
import numpy as np
from PIL import Image

from core.config import settings

if settings.BASE_DIR not in sys.path:
    sys.path.append(settings.BASE_DIR)

from Frame.frame_processor import stylize_a, stylize_b, stylize_c, cv2_to_pil
from Frame.manga_layout import generate_manga_layout, create_manga_page
from Frame.detection import PersonSegmenter
import uuid

segmenter = PersonSegmenter()

def draw_masks_on_image(image_np, masks, color=(255, 0, 0), alpha=0.5):
    """
    Draw red masks on the image (RGB).
    """
    # Create a copy to avoid modifying the original if shared
    result = image_np.copy()
    
    for mask in masks:
        mask_indices = mask > 0
        if len(mask_indices.shape) == 2:
            # Binary mask, broadcast to 3 channels
            result[mask_indices] = (result[mask_indices] * (1 - alpha) + np.array(color) * alpha).astype(np.uint8)
            
    return result

async def process_manga_generation(
    image_paths, 
    width=1000, 
    height=1400, 
    num_frames=8, 
    seed=42, 
    stylize_style='c', 
    segment_human=False, 
    show_mask=False):
    
    processed_images = []
    
    for path in image_paths:
        # Stylize
        if stylize_style == 'a':
            processed_cv2 = stylize_a(path)
        elif stylize_style == 'b':
            processed_cv2 = stylize_b(path)
        elif stylize_style == 'c':
            processed_cv2 = stylize_c(path)
        else:
            processed_cv2 = stylize_c(path)
            
        if processed_cv2 is None:
            # Fallback to original image if processing fails
            img = cv2.imread(path)
            if img is not None:
                processed_cv2 = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else:
                continue # Skip if image cannot be read

        # Human Segmentation
        if segment_human:
            try:
                # Segment on the original image for better accuracy
                _, _, person_masks, _ = segmenter.segment(path)
                
                if show_mask and person_masks:
                    # Draw masks on the stylized image (in RGB)
                    processed_cv2 = draw_masks_on_image(processed_cv2, person_masks)
            except Exception as e:
                print(f"Error during human segmentation for {path}: {e}")

        pil_img = cv2_to_pil(processed_cv2)
        processed_images.append(pil_img)

    if not processed_images:
        raise ValueError("No images were successfully processed.")

    # Handle chunking into multiple pages
    actual_num_frames = num_frames if num_frames > 0 else len(processed_images)
    
    manga_urls = []
    
    for i in range(0, len(processed_images), actual_num_frames):
        chunk = processed_images[i:i + actual_num_frames]
        
        # Fill remaining frames with blank white images if chunk is too small
        current_chunk_size = len(chunk)
        if current_chunk_size < actual_num_frames:
            blank_img = Image.new('RGB', (100, 100), "white")
            for j in range(actual_num_frames - current_chunk_size):
                chunk.append(blank_img)

        # Generate Layout
        frames = generate_manga_layout(
            width=width,
            height=height,
            num_frames=actual_num_frames,
            seed=seed + i, 
            std_dev=0.05,
            margin=8
        )

        # Create Manga Page
        manga_page = create_manga_page(
            images=chunk,
            frames=frames,
            width=width,
            height=height,
            bg_color="white"
        )

        # Save Result
        output_filename = f"manga_{uuid.uuid4()}.png"
        output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
        manga_page.save(output_path)
        
        manga_urls.append(f"/output/{output_filename}")
        
    return manga_urls
