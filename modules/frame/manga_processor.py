import os
import cv2
import uuid
import random
import numpy as np
from PIL import Image, ImageOps, JpegImagePlugin, PdfImagePlugin
Image.init()

from core.config import settings
from modules.frame.human_detector import PersonSegmenter

# Lazy-loaded instance segmenter
segmenter = PersonSegmenter()

# --- Image Utilities & Clear Checks ---

def cv2_to_pil(cv2_image: np.ndarray) -> Image.Image:
    """Converts an OpenCV image (BGR or Gray) to a PIL Image (RGB).

    Args:
        cv2_image (np.ndarray): OpenCV image array.

    Returns:
        Image.Image: Converted PIL Image.
    """
    if len(cv2_image.shape) == 2:
        rgb = cv2.cvtColor(cv2_image, cv2.COLOR_GRAY2RGB)
    else:
        rgb = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)

def frame_clear(image_path: str, blur_threshold: float = 100.0, brightness_threshold: float = 50.0) -> tuple:
    """Checks if an image frame is clear (sharp and bright enough) for manga processing.

    Args:
        image_path (str): Path to input image file.
        blur_threshold (float): Minimum variance of Laplacian for blur detection.
        brightness_threshold (float): Minimum mean grayscale value for brightness.

    Returns:
        tuple: (is_clear: bool, reason: str).
    """
    img = cv2.imread(image_path)
    if img is None:
        return False, "Failed to load image."

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < blur_threshold:
        return False, f"Too blurry ({laplacian_var:.2f} < {blur_threshold})"

    avg_brightness = float(np.mean(gray))
    if avg_brightness < brightness_threshold:
        return False, f"Too dark ({avg_brightness:.2f} < {brightness_threshold})"

    return True, "Clear"

def _load_image(image_input) -> np.ndarray:
    """Loads image from file path string or returns copy of NumPy array."""
    if isinstance(image_input, str):
        return cv2.imread(image_input)
    elif isinstance(image_input, np.ndarray):
        return image_input.copy()
    return None

# --- Stylization Filters ---

def stylize_a(image_input, output_path: str = None) -> np.ndarray:
    """Pipeline A: Classic Black & White Manga (CLAHE Contrast + Adaptive Thresholding).

    Args:
        image_input (str or np.ndarray): File path or OpenCV image array.
        output_path (str, optional): Target file path to save image.

    Returns:
        np.ndarray: Stylized RGB image array.
    """
    img = _load_image(image_input)
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    enhanced_gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    edges = cv2.adaptiveThreshold(enhanced_gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9)
    result = cv2.bitwise_and(enhanced_gray, enhanced_gray, mask=edges)
    result = cv2.cvtColor(result, cv2.COLOR_GRAY2RGB)
    if output_path:
        cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
    return result

def stylize_b(image_input, output_path: str = None) -> np.ndarray:
    """Pipeline B: Anime-style Coloring (Iterative Bilateral Filter + Median Blur Edges).

    Args:
        image_input (str or np.ndarray): File path or OpenCV image array.
        output_path (str, optional): Target file path to save image.

    Returns:
        np.ndarray: Stylized RGB image array.
    """
    img = _load_image(image_input)
    if img is None:
        return None
    color = img.copy()
    for _ in range(3):
        color = cv2.bilateralFilter(color, d=9, sigmaColor=75, sigmaSpace=75)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.adaptiveThreshold(cv2.medianBlur(gray, 7), 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 2)
    result = cv2.bitwise_and(color, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR))
    result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    if output_path:
        cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
    return result

def stylize_c(image_input, output_path: str = None) -> np.ndarray:
    """Pipeline C: Comic Book Effect (Edge-Preserving Filter).

    Args:
        image_input (str or np.ndarray): File path or OpenCV image array.
        output_path (str, optional): Target file path to save image.

    Returns:
        np.ndarray: Stylized RGB image array.
    """
    img = _load_image(image_input)
    if img is None:
        return None
    result = cv2.edgePreservingFilter(img, flags=1, sigma_s=40, sigma_r=0.3)
    result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    if output_path:
        cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
    return result

def create_manga_pipeline(image_paths: list, stylize_style: str = 'c', width: int = 1000, height: int = 1400, bg_color: str = "white", seed: int = None):
    """Full pipeline: clear check -> stylize -> layout -> generate page."""
    processed_images = []
    for path in image_paths:
        is_clear, reason = frame_clear(path)
        if not is_clear:
            print(f"Warning: {os.path.basename(path)} is {reason}")
            
        if stylize_style == 'a':
            processed = stylize_a(path)
        elif stylize_style == 'b':
            processed = stylize_b(path)
        elif stylize_style == 'c':
            processed = stylize_c(path)
        else:
            raise ValueError("Style must be 'a', 'b', or 'c'")
            
        if processed is None:
            raise FileNotFoundError(f"Failed to process {path}")
        processed_images.append(cv2_to_pil(processed))

    frames = generate_manga_layout(width=width, height=height, num_frames=len(image_paths), seed=seed)
    return create_manga_page(images=processed_images, frames=frames, width=width, height=height, bg_color=bg_color)

# --- Layout Generator ---

def generate_manga_layout(
    width: int = 1000,
    height: int = 1400,
    num_frames: int = 8,
    seed: int = None,
    std_dev: float = 0.1,
    margin: int = 10,
    min_ratio: float = 0.3
) -> list:
    """Generates ordered rectangular panel frames using a recursive splitting tree algorithm.

    Args:
        width (int): Canvas total width.
        height (int): Canvas total height.
        num_frames (int): Target number of panels.
        seed (int, optional): Random seed for reproducibility.
        std_dev (float): Split ratio standard deviation.
        margin (int): Margin padding around each panel in pixels.
        min_ratio (float): Minimum split ratio boundary.

    Returns:
        list: List of (x, y, w, h) frame bounding box tuples.
    """
    if seed is not None:
        random.seed(seed)
    root = {"rect": (0, 0, width, height), "left": None, "right": None}
    leaves = [root]
    
    while len(leaves) < num_frames:
        best_idx, max_score = 0, 0
        for i, node in enumerate(leaves):
            _, _, w, h = node["rect"]
            score = (w * h) * (max(w / h, h / w) ** 1.5)
            if score > max_score:
                max_score, best_idx = score, i
                
        node = leaves.pop(best_idx)
        x, y, w, h = node["rect"]
        aspect = w / h
        
        direction = 'vertical' if aspect >= 1.25 else 'horizontal' if aspect <= 0.8 else random.choice(['v', 'h'])
        ratio = max(min_ratio, min(1.0 - min_ratio, random.normalvariate(0.5, std_dev)))
        
        if direction in ['vertical', 'v']:
            w1 = int(w * ratio)
            node["left"] = {"rect": (x, y, w1, h), "left": None, "right": None}
            node["right"] = {"rect": (x + w1, y, w - w1, h), "left": None, "right": None}
        else:
            h1 = int(h * ratio)
            node["left"] = {"rect": (x, y, w, h1), "left": None, "right": None}
            node["right"] = {"rect": (x, y + h1, w, h - h1), "left": None, "right": None}
        leaves.extend([node["left"], node["right"]])
        
    def _get_rects(n):
        return [n["rect"]] if not n["left"] else _get_rects(n["left"]) + _get_rects(n["right"])
    
    return [
        (x + margin, y + margin, w - 2 * margin, h - 2 * margin)
        if w > 2 * margin and h > 2 * margin else (x, y, w, h)
        for (x, y, w, h) in _get_rects(root)
    ]

def create_manga_page(images: list, frames: list, width: int = 1000, height: int = 1400, bg_color: str = "white") -> Image.Image:
    """Composites processed panel images into the generated layout using Pillow LANCZOS resampling.

    Args:
        images (list): List of PIL.Image objects or image file paths.
        frames (list): List of (x, y, w, h) frame bounding boxes.
        width (int): Canvas total width.
        height (int): Canvas total height.
        bg_color (str): Page background color.

    Returns:
        Image.Image: Composited manga page PIL image.
    """
    if len(images) != len(frames):
        raise ValueError("Mismatch between images and frames count")
    page = Image.new("RGB", (width, height), bg_color)
    for img_input, (x, y, w, h) in zip(images, frames):
        img = Image.open(img_input) if isinstance(img_input, str) else img_input.copy()
        page.paste(ImageOps.fit(img.convert('RGB'), (int(w), int(h)), method=Image.Resampling.LANCZOS), (int(x), int(y)))
    return page

def create_bubble_mask(image_shape: tuple, axes: tuple, character_mask: np.ndarray = None, proximity_target: tuple = None, num_persons: int = 1) -> tuple:
    """Finds optimal placement for an oval bubble, avoiding character overlap.

    Args:
        image_shape (tuple): Canvas (H, W) tuple.
        axes (tuple): Bubble (bw, bh) dimensions.
        character_mask (np.ndarray, optional): Binary mask of person instances.
        proximity_target (tuple, optional): Target speaker centroid.
        num_persons (int): Number of detected persons.

    Returns:
        tuple: (bubble_mask, (cx, cy)).
    """
    h, w = image_shape[:2]
    bw, bh = axes
    template = np.zeros((bh, bw), dtype=np.uint8)
    cv2.ellipse(template, (bw // 2, bh // 2), (bw // 2, bh // 2), 0, 0, 360, 255, -1)
    
    if character_mask is not None:
        char_m = (character_mask > 0).astype(np.uint8) * 255
        overlap_map = cv2.matchTemplate(char_m, template, cv2.TM_CCORR)
        
        if proximity_target:
            px, py = proximity_target
            xs, ys = np.arange(overlap_map.shape[1]) + bw // 2, np.arange(overlap_map.shape[0]) + bh // 2
            xv, yv = np.meshgrid(xs, ys)
            dist = np.sqrt((xv - px) ** 2 + (yv - py) ** 2)
            penalty = dist * (255.0 * bw * bh) * (0.005 / max(1, num_persons))
            pad_x, pad_y = bw // 2 + 5, bh // 2 + 5
            if pad_x < overlap_map.shape[1]:
                overlap_map[:, :pad_x] = overlap_map[:, -pad_x:] = float('inf')
            if pad_y < overlap_map.shape[0]:
                overlap_map[:pad_y, :] = overlap_map[-pad_y:, :] = float('inf')
            overlap_map += penalty.astype(np.float32)
            
        _, _, min_loc, _ = cv2.minMaxLoc(overlap_map)
        cx, cy = min_loc[0] + bw // 2, min_loc[1] + bh // 2
    else:
        cx, cy = w // 2, h // 4
        
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.ellipse(mask, (cx, cy), (bw // 2, bh // 2), 0, 0, 360, 255, -1)
    return mask, (cx, cy)

# --- High-Level Orchestration & PDF Export ---

def draw_masks(image_np: np.ndarray, masks: list, color: tuple = (255, 0, 0), alpha: float = 0.5) -> np.ndarray:
    """Draws binary segmentation masks onto an image array for visualization."""
    result = image_np.copy()
    for mask in masks:
        idx = mask > 0
        if len(idx.shape) == 2:
            result[idx] = (result[idx] * (1 - alpha) + np.array(color) * alpha).astype(np.uint8)
    return result

async def process_manga_generation(
    image_paths: list,
    width: int = 1000,
    height: int = 1400,
    num_frames: int = 8, 
    seed: int = 42,
    stylize_style: str = 'c',
    segment_human: bool = False,
    show_mask: bool = False
) -> list:
    """Master pipeline converting a list of image files into multi-page manga PNG URLs."""
    processed_images = []
    
    for path in image_paths:
        stylizer_map = {'a': stylize_a, 'b': stylize_b, 'c': stylize_c}
        proc_cv2 = stylizer_map.get(stylize_style, stylize_c)(path)
            
        if proc_cv2 is None:
            img = cv2.imread(path)
            if img is not None:
                proc_cv2 = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else:
                continue

        if segment_human:
            try:
                _, _, masks, _ = segmenter.segment(path)
                if show_mask and masks:
                    proc_cv2 = draw_masks(proc_cv2, masks)
            except Exception as e:
                print(f"Segmentation error for {path}: {e}")

        processed_images.append(cv2_to_pil(proc_cv2))

    if not processed_images:
        raise ValueError("No images processed.")

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

def save_manga_pages_to_pdf(
    page_images: list,
    output_pdf_path: str = None
) -> str:
    """Combines a list of PIL Images or image file paths into a single multi-page PDF document.

    Args:
        page_images (list): List of PIL.Image objects or image file paths (str).
        output_pdf_path (str, optional): Target PDF output path.

    Returns:
        str: Absolute path to the generated multi-page PDF document.
    """
    if not page_images:
        raise ValueError("Cannot generate PDF from empty page images list.")

    if output_pdf_path is None:
        output_pdf_path = os.path.join(settings.OUTPUT_DIR, "manga_volume.pdf")

    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)

    pil_pages = []
    for item in page_images:
        if isinstance(item, str):
            if os.path.exists(item):
                img = Image.open(item).convert("RGB")
                pil_pages.append(img)
            else:
                print(f"Warning: Image file not found at {item}, skipping for PDF export.")
        elif isinstance(item, Image.Image):
            pil_pages.append(item.convert("RGB"))

    if not pil_pages:
        raise ValueError("No valid image pages could be loaded for PDF export.")

    first_page = pil_pages[0]
    remaining_pages = pil_pages[1:]

    first_page.save(
        output_pdf_path,
        format="PDF",
        save_all=True,
        append_images=remaining_pages
    )

    print(f"Successfully created multi-page manga PDF with {len(pil_pages)} pages at: {output_pdf_path}")
    return os.path.abspath(output_pdf_path)

