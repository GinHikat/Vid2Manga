import cv2
import numpy as np
from PIL import Image

def frame_clear(image_path, blur_threshold=100.0, brightness_threshold=50):
    """
    Checks if a frame is clear enough for processing.
    Returns a tuple: (is_clear: bool, reason: str if not clear)
    
    Args:
        image_path: Path to the image file.
        blur_threshold: Minimum variance of Laplacian to be considered "sharp".
        brightness_threshold: Minimum average brightness.
    """
    img = cv2.imread(image_path)
    if img is None:
        return False, "Failed to load image."

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Blur Detection using Variance of Laplacian
    # A sharp image will have a higher variance (more edges).
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < blur_threshold:
        return False, f"Too blurry (Score: {laplacian_var:.2f} < {blur_threshold})"

    # Brightness Check
    # Ensure the image isn't pitch black or extremely dark
    avg_brightness = np.mean(gray)
    if avg_brightness < brightness_threshold:
        return False, f"Too dark (Brightness: {avg_brightness:.2f} < {brightness_threshold})"

    return True, f"Clear (Blur Score: {laplacian_var:.2f}, Brightness: {avg_brightness:.2f})"

def stylize_pipeline_a(image_path, output_path=None):
    """
    Pipeline A: Classic Black & White Manga (OpenCV Only)
    High contrast, sharp edges, grayscale.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None

    # Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(gray)

    # Edge Detection/Line Art (Adaptive Thresholding)
    # This creates a binary image (black lines on white background)
    edges = cv2.adaptiveThreshold(
        enhanced_gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9
    )

    # Blend
    # blend the line art back with the original grayscale for some depth. Or just return the harsh line art depending on preference. Let's do a harsh blend.
    result = cv2.bitwise_and(enhanced_gray, enhanced_gray, mask=edges)

    # Convert back to RGB for matplotlib/PIL rendering
    result = cv2.cvtColor(result, cv2.COLOR_GRAY2RGB)

    if output_path:
        cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
        
    return result

def stylize_pipeline_b(image_path, output_path=None):
    """
    Pipeline B: Anime-style Coloring / Cel-shaded (OpenCV)
    Smoothed colors with sharp edges.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None

    # Smoothing (Bilateral Filter)
    # Bilateral filter smooths flat regions while preserving edges. We run it multiple times for a painted look.
    color = img.copy()
    for _ in range(3): 
        color = cv2.bilateralFilter(color, d=9, sigmaColor=75, sigmaSpace=75)

    # Edge Detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Use median blur to reduce noise before edge detection
    gray_blur = cv2.medianBlur(gray, 7)
    edges = cv2.adaptiveThreshold(
        gray_blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 2
    )
    
    # Convert edges to BGR so we can combine it with the color image
    edges_color = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    # Make the edges slightly less harsh by weighting them and just return
    result = cv2.bitwise_and(color, edges_color)

    # Convert back to RGB for matplotlib/PIL rendering
    result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)

    if output_path:
        cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
        
    return result

def stylize_pipeline_c(image_path, output_path=None):
    """
    Pipeline C: Neural Style Transfer / Edge-Preserving Filter Simulation
    Since running a full deep learning model (like AnimeGAN) requires downloading weights 
    and heavy setup, this is a lightweight OpenCV simulation of a "comic book" effect 
    using Edge Preserving Filter and Stylization.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None

    # Edge Preserving Filter (maintains color better than heavy stylization)
    result = cv2.edgePreservingFilter(img, flags=1, sigma_s=40, sigma_r=0.3)

    # Convert back to RGB for matplotlib/PIL rendering
    result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)

    if output_path:
        cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
        
    return result

# --- Helper conversion for Pillow (so we can use it with create_manga_page) ---
def cv2_to_pil(cv2_image):
    """Converts a loaded OpenCV image (RGB or Gray) to a PIL Image (RGB)"""
    if len(cv2_image.shape) == 2:
        # Grayscale
        rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_GRAY2RGB)
    else:
        # Image is already RGB from the stylization pipelines
        rgb_image = cv2_image
    return Image.fromarray(rgb_image)
