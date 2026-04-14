import cv2
import numpy as np
import os
from PIL import Image

def frame_clear(image_path, blur_threshold=100.0, brightness_threshold=50):
    """Checks if a frame is clear (sharp and bright enough) for processing."""
    img = cv2.imread(image_path)
    if img is None: return False, "Failed to load image."

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < blur_threshold:
        return False, f"Too blurry ({laplacian_var:.2f} < {blur_threshold})"

    avg_brightness = np.mean(gray)
    if avg_brightness < brightness_threshold:
        return False, f"Too dark ({avg_brightness:.2f} < {brightness_threshold})"

    return True, "Clear"

def stylize_a(image_path, output_path=None):
    """Pipeline A: Classic Black & White Manga (Contrast + Adaptive Threshold)."""
    img = cv2.imread(image_path)
    if img is None: return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    enhanced_gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    edges = cv2.adaptiveThreshold(enhanced_gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9)
    result = cv2.bitwise_and(enhanced_gray, enhanced_gray, mask=edges)
    result = cv2.cvtColor(result, cv2.COLOR_GRAY2RGB)
    if output_path: cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
    return result

def stylize_b(image_path, output_path=None):
    """Pipeline B: Anime-style Coloring (Bilateral Filter + Edges)."""
    img = cv2.imread(image_path)
    if img is None: return None
    color = img.copy()
    for _ in range(3): 
        color = cv2.bilateralFilter(color, d=9, sigmaColor=75, sigmaSpace=75)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.adaptiveThreshold(cv2.medianBlur(gray, 7), 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 2)
    result = cv2.bitwise_and(color, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR))
    result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    if output_path: cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
    return result

def stylize_c(image_path, output_path=None):
    """Pipeline C: Comic book effect (Edge-Preserving Filter)."""
    img = cv2.imread(image_path)
    if img is None: return None
    result = cv2.edgePreservingFilter(img, flags=1, sigma_s=40, sigma_r=0.3)
    result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    if output_path: cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
    return result

def cv2_to_pil(cv2_image):
    """Converts OpenCV image to PIL Image (RGB)."""
    rgb = cv2.cvtColor(cv2_image, cv2.COLOR_GRAY2RGB) if len(cv2_image.shape) == 2 else cv2_image
    return Image.fromarray(rgb)

def create_manga_pipeline(image_paths, stylize_style='c', width=1000, height=1400, bg_color="white", seed=None):
    """Full pipeline: clear check -> stylize -> layout -> generate page."""
    from .layout_generator import generate_manga_layout, create_manga_page
    
    processed_images = []
    for path in image_paths:
        is_clear, reason = frame_clear(path)
        if not is_clear: print(f"Warning: {os.path.basename(path)} is {reason}")
            
        if stylize_style == 'a': processed = stylize_a(path)
        elif stylize_style == 'b': processed = stylize_b(path)
        elif stylize_style == 'c': processed = stylize_c(path)
        else: raise ValueError("Style must be 'a', 'b', or 'c'")
            
        if processed is None: raise FileNotFoundError(f"Failed to process {path}")
        processed_images.append(cv2_to_pil(processed))

    frames = generate_manga_layout(width=width, height=height, num_frames=len(image_paths), seed=seed)
    return create_manga_page(images=processed_images, frames=frames, width=width, height=height, bg_color=bg_color)
