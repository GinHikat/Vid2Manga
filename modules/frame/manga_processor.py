import os
import cv2
import uuid
import random
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont, JpegImagePlugin, PdfImagePlugin
Image.init()

from core.config import settings
from modules.frame.human_detector import PersonSegmenter

# Lazy-loaded instance segmenter
_segmenter = None

def get_segmenter():
    """Lazy-loads PersonSegmenter instance on first access."""
    global _segmenter
    if _segmenter is None:
        _segmenter = PersonSegmenter()
    return _segmenter

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
    
    min_w = 260
    min_h = 240

    while len(leaves) < num_frames:
        candidates = []
        for i, node in enumerate(leaves):
            _, _, w, h = node["rect"]
            can_v = w >= 2 * min_w
            can_h = h >= 2 * min_h
            if can_v or can_h:
                aspect = w / h
                score = (w * h) * (max(aspect, 1.0 / max(aspect, 0.01)) ** 1.5)
                candidates.append((score, i, can_v, can_h))

        if not candidates:
            break

        candidates.sort(key=lambda c: c[0], reverse=True)
        _, best_idx, can_v, can_h = candidates[0]
        node = leaves.pop(best_idx)
        x, y, w, h = node["rect"]
        aspect = w / h

        if can_v and can_h:
            direction = 'v' if aspect >= 1.2 else 'h' if aspect <= 0.8 else random.choice(['v', 'h'])
        elif can_v:
            direction = 'v'
        else:
            direction = 'h'

        ratio = max(0.35, min(0.65, random.normalvariate(0.5, std_dev)))

        if direction == 'v':
            w1 = max(min_w, min(w - min_w, int(w * ratio)))
            node["left"] = {"rect": (x, y, w1, h), "left": None, "right": None}
            node["right"] = {"rect": (x + w1, y, w - w1, h), "left": None, "right": None}
        else:
            h1 = max(min_h, min(h - min_h, int(h * ratio)))
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
    page = Image.new("RGB", (width, height), bg_color)
    draw_page = ImageDraw.Draw(page)
    for img_input, (x, y, w, h) in zip(images, frames):
        img = Image.open(img_input) if isinstance(img_input, str) else img_input.copy()
        fitted = ImageOps.fit(img.convert('RGB'), (int(w), int(h)), method=Image.Resampling.LANCZOS)
        page.paste(fitted, (int(x), int(y)))
        draw_page.rectangle([int(x), int(y), int(x + w), int(y + h)], outline="black", width=2)
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
                _, _, masks, _ = get_segmenter().segment(path)
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

def _create_bubble_canvas_with_tail(bw: int, bh: int, tail_angle_deg: float = 120.0, tail_len: int = 25) -> np.ndarray:
    """Creates a white speech bubble canvas with a black outline border and a directional tail pointing toward the speaker.

    Args:
        bw (int): Main bubble body width.
        bh (int): Main bubble body height.
        tail_angle_deg (float): Angle in degrees pointing from bubble center toward speaker.
        tail_len (int): Length of tail extension in pixels.

    Returns:
        np.ndarray: OpenCV BGR image array containing the bubble body and tail.
    """
    margin = tail_len + 5
    canvas_w = bw + margin * 2
    canvas_h = bh + margin * 2
    img = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)

    cx, cy = canvas_w // 2, canvas_h // 2
    rx, ry = bw // 2 - 4, bh // 2 - 4

    angle_rad = np.deg2rad(tail_angle_deg)
    vx, vy = np.cos(angle_rad), np.sin(angle_rad)

    spread_rad = np.deg2rad(22.0)
    p1_x = int(cx + rx * np.cos(angle_rad - spread_rad))
    p1_y = int(cy + ry * np.sin(angle_rad - spread_rad))
    p2_x = int(cx + rx * np.cos(angle_rad + spread_rad))
    p2_y = int(cy + ry * np.sin(angle_rad + spread_rad))

    tip_x = int(cx + (rx + tail_len) * vx)
    tip_y = int(cy + (ry + tail_len) * vy)

    tail_poly = np.array([[p1_x, p1_y], [tip_x, tip_y], [p2_x, p2_y]], dtype=np.int32)

    # Fill white interior
    cv2.ellipse(img, (cx, cy), (rx, ry), 0, 0, 360, (255, 255, 255), -1)
    cv2.fillPoly(img, [tail_poly], (255, 255, 255))

    # Black stroke outline
    cv2.ellipse(img, (cx, cy), (rx, ry), 0, 0, 360, (0, 0, 0), 3)
    cv2.line(img, (p1_x, p1_y), (tip_x, tip_y), (0, 0, 0), 3)
    cv2.line(img, (p2_x, p2_y), (tip_x, tip_y), (0, 0, 0), 3)

    # Erase inner ellipse arc between tail base points
    inner_poly = np.array([[p1_x, p1_y], [int(cx + (rx - 4) * vx), int(cy + (ry - 4) * vy)], [p2_x, p2_y]], dtype=np.int32)
    cv2.fillPoly(img, [inner_poly], (255, 255, 255))

    return img

def create_manga_page_with_dialogue(
    frame_dialogue_pairs: list[dict],
    stylize_style: str = 'c',
    width: int = 1000,
    height: int = 1400,
    bg_color: str = "white",
    enable_bubbles: bool = True,
    seed: int = None,
    global_speaker_map: dict = None
) -> Image.Image:
    """Composites stylized frames with character detection, speech bubbles, and dialogue alignment.

    Args:
        frame_dialogue_pairs (list[dict]): List of matched keyframe + speech segment dicts.
        stylize_style (str): Artistic filter choice ('a': B&W, 'b': color anime, 'c': comic).
        width (int): Canvas total width in pixels (default: 1000).
        height (int): Canvas total height in pixels (default: 1400).
        bg_color (str): Page background color (default: "white").
        enable_bubbles (bool): Whether to typeset and overlay speech bubbles.
        seed (int, optional): Optional random seed for panel layout splitting reproducibility.
        global_speaker_map (dict, optional): Persistent context dictionary mapping speakers to person indices.

    Returns:
        Image.Image: Composited manga page PIL Image.
    """
    if not frame_dialogue_pairs:
        raise ValueError("Cannot create manga page from empty frame dialogue pairs list.")

    if global_speaker_map is None:
        global_speaker_map = {}

    num_panels = len(frame_dialogue_pairs)
    frames = generate_manga_layout(width=width, height=height, num_frames=num_panels, seed=seed)
    
    page = Image.new("RGB", (width, height), bg_color)
    draw_page = ImageDraw.Draw(page)
    stylizer_map = {'a': stylize_a, 'b': stylize_b, 'c': stylize_c}
    stylizer_func = stylizer_map.get(stylize_style, stylize_c)

    from modules.frame.bubble_processor import Bubble, find_optimal_bubble_center

    bubble_tool = Bubble()

    for pair, (x, y, w, h) in zip(frame_dialogue_pairs, frames):
        img_path = pair.get("keyframe_path") or pair.get("path")
        if not img_path or not os.path.exists(img_path):
            panel_pil = Image.new("RGB", (int(w), int(h)), "gray")
        else:
            proc_cv2 = stylizer_func(img_path)
            if proc_cv2 is None:
                orig = cv2.imread(img_path)
                proc_cv2 = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB) if orig is not None else np.zeros((int(h), int(w), 3), dtype=np.uint8)
            panel_pil = Image.fromarray(proc_cv2)

        # Fit panel image into layout frame bounding box
        panel_fitted = ImageOps.fit(panel_pil.convert("RGB"), (int(w), int(h)), method=Image.Resampling.LANCZOS)
        panel_bgr = cv2.cvtColor(np.array(panel_fitted), cv2.COLOR_RGB2BGR)

        # Speech bubble typesetting and overlay
        dialogue_text = (pair.get("dialogue") or "").strip()
        raw_turns = pair.get("dialogue_by_speaker") or []
        if not raw_turns and dialogue_text:
            raw_turns = [{"speaker": pair.get("speaker", "Unknown Speaker"), "text": dialogue_text}]

        # Merge turns from the SAME speaker into 1 single turn per speaker
        merged_turns_map = {}
        for t in raw_turns:
            spk_key = t.get("speaker", "Unknown Speaker")
            txt_val = (t.get("text") or "").strip()
            if txt_val:
                if spk_key not in merged_turns_map:
                    merged_turns_map[spk_key] = []
                merged_turns_map[spk_key].append(txt_val)

        speaker_turns = [
            {"speaker": spk_key, "text": " ".join(txt_list)}
            for spk_key, txt_list in merged_turns_map.items()
        ]

        if enable_bubbles and speaker_turns:
            try:
                # Segment character instances inside panel
                _, _, masks, _ = get_segmenter().segment(panel_bgr)
                
                person_centroids = []
                total_person_mask = np.zeros(panel_bgr.shape[:2], dtype=np.uint8)

                if masks:
                    for m in masks:
                        m_uint8 = m.astype(np.uint8)
                        total_person_mask = cv2.bitwise_or(total_person_mask, m_uint8)
                        moments = cv2.moments(m_uint8)
                        if moments["m00"] > 0:
                            mcx = int(moments["m10"] / moments["m00"])
                            mcy = int(moments["m01"] / moments["m00"])
                            person_centroids.append((mcx, mcy, m_uint8))

                person_centroids.sort(key=lambda item: item[0])
                face_head_mask = np.zeros(panel_bgr.shape[:2], dtype=np.uint8)

                for mcx, mcy, m_uint8 in person_centroids:
                    ys, xs = np.where(m_uint8 > 0)
                    if len(ys) > 0:
                        ymin, ymax = np.min(ys), np.max(ys)
                        head_cutoff = int(ymin + 0.40 * (ymax - ymin))
                        head_submask = np.zeros_like(m_uint8)
                        head_submask[ymin:head_cutoff, :] = m_uint8[ymin:head_cutoff, :]
                        face_head_mask = cv2.bitwise_or(face_head_mask, head_submask)

                unique_speakers = list(dict.fromkeys([t["speaker"] for t in speaker_turns]))
                speaker_to_person = {}

                for s_idx, spk in enumerate(unique_speakers):
                    if spk not in global_speaker_map and spk not in ["Unknown Speaker", "Unknown"]:
                        if "0" in str(spk):
                            global_speaker_map[spk] = 0
                        elif "1" in str(spk):
                            global_speaker_map[spk] = 1
                        else:
                            global_speaker_map[spk] = len(global_speaker_map)

                    p_idx = global_speaker_map.get(spk, s_idx)
                    if p_idx < len(person_centroids):
                        speaker_to_person[spk] = person_centroids[p_idx]
                    else:
                        speaker_to_person[spk] = None

                placed_bubbles_mask = np.zeros(panel_bgr.shape[:2], dtype=np.uint8)
                person_coverage = np.sum(total_person_mask > 0) / (float(w * h) or 1.0)

                # Process each unique speaker in panel
                for turn in speaker_turns:
                    spk = turn.get("speaker", "Unknown Speaker")
                    txt = (turn.get("text") or "").strip()
                    if not txt:
                        continue

                    # Dynamic font size reduction and word wrapping to fit ellipse bounds
                    bubble_w = max(160, min(int(w * 0.70), len(txt) * 6 + 40))
                    bubble_h = max(100, min(int(h * 0.40), len(txt) * 3 + 35))

                    font_size = 15
                    min_font_size = 8
                    selected_font = None
                    selected_lines = []
                    selected_line_height = 18

                    dummy_img = Image.new("RGB", (1, 1))
                    d_dummy = ImageDraw.Draw(dummy_img)

                    while font_size >= min_font_size:
                        try:
                            font = ImageFont.truetype("arial.ttf", font_size)
                        except Exception:
                            font = ImageFont.load_default()

                        line_height = font_size + 4
                        max_chars = max(10, int((bubble_w * 0.70) / max(3.0, font_size * 0.55)))

                        words = txt.split()
                        test_lines = []
                        curr_line = []
                        for word in words:
                            curr_line.append(word)
                            if len(" ".join(curr_line)) > max_chars:
                                curr_line.pop()
                                if curr_line:
                                    test_lines.append(" ".join(curr_line))
                                curr_line = [word]
                        if curr_line:
                            test_lines.append(" ".join(curr_line))

                        tot_h = len(test_lines) * line_height
                        max_w = max([d_dummy.textbbox((0, 0), l, font=font)[2] for l in test_lines]) if test_lines else 0

                        if tot_h <= bubble_h * 0.70 and max_w <= bubble_w * 0.72:
                            selected_font = font
                            selected_lines = test_lines
                            selected_line_height = line_height
                            break

                        font_size -= 1

                    if selected_font is None:
                        try:
                            selected_font = ImageFont.truetype("arial.ttf", min_font_size)
                        except Exception:
                            selected_font = ImageFont.load_default()
                        selected_line_height = min_font_size + 3
                        words = txt.split()
                        selected_lines = []
                        curr_line = []
                        for word in words:
                            curr_line.append(word)
                            if len(" ".join(curr_line)) > 15:
                                curr_line.pop()
                                if curr_line:
                                    selected_lines.append(" ".join(curr_line))
                                curr_line = [word]
                        if curr_line:
                            selected_lines.append(" ".join(curr_line))

                    speaker_idx = global_speaker_map.get(spk, 0)
                    preferred_side = "left" if speaker_idx == 0 else "right"

                    box_half_w = bubble_w // 2
                    box_half_h = bubble_h // 2
                    margin_x = box_half_w + 10
                    margin_y = box_half_h + 10

                    # For close-up shots or top corners, force cy = margin_y
                    opt_cx, opt_cy = find_optimal_bubble_center(
                        total_person_mask=total_person_mask,
                        bubble_w=bubble_w,
                        bubble_h=bubble_h,
                        preferred_side=preferred_side,
                        y_max=margin_y if person_coverage > 0.35 else int(h * 0.40)
                    )

                    candidate_positions = [
                        (margin_x if preferred_side == "left" else int(w) - margin_x, margin_y),
                        (opt_cx, margin_y if person_coverage > 0.35 else opt_cy),
                        (int(w) - margin_x if preferred_side == "left" else margin_x, margin_y),
                        (margin_x if preferred_side == "left" else int(w) - margin_x, int(h) - margin_y)
                    ]

                    best_pos = None
                    best_penalty = float('inf')

                    for cand_cx, cand_cy in candidate_positions:
                        c_cx = max(margin_x, min(int(w) - margin_x, cand_cx))
                        c_cy = max(margin_y, min(int(h) - margin_y, cand_cy))

                        test_body = np.zeros(panel_bgr.shape[:2], dtype=np.uint8)
                        cv2.ellipse(test_body, (c_cx, c_cy), (box_half_w, box_half_h), 0, 0, 360, 255, -1)

                        face_overlap = np.sum((test_body > 0) & (face_head_mask > 0))
                        bubble_overlap = np.sum((test_body > 0) & (placed_bubbles_mask > 0))
                        person_overlap = np.sum((test_body > 0) & (total_person_mask > 0))

                        penalty = (bubble_overlap * 100000.0) + (face_overlap * 10000.0) + person_overlap

                        if penalty < best_penalty:
                            best_penalty = penalty
                            best_pos = (c_cx, c_cy)

                    cx, cy = best_pos if best_pos else (margin_x if preferred_side == "left" else int(w) - margin_x, margin_y)
                    body_mask = np.zeros(panel_bgr.shape[:2], dtype=np.uint8)
                    cv2.ellipse(body_mask, (cx, cy), (box_half_w, box_half_h), 0, 0, 360, 255, -1)

                    # Register placed bubble to prevent subsequent bubble overlap
                    cv2.ellipse(placed_bubbles_mask, (cx, cy), (box_half_w + 15, box_half_h + 15), 0, 0, 360, 255, -1)

                    matched_person = speaker_to_person.get(spk)

                    if matched_person is not None:
                        # Visible speaker character: attach tail pointing to speaker centroid
                        char_x, char_y = matched_person[0], matched_person[1]
                        dx = char_x - cx
                        dy = char_y - cy
                        tail_angle_deg = np.rad2deg(np.arctan2(dy, dx))

                        tail_mask = np.zeros(panel_bgr.shape[:2], dtype=np.uint8)
                        base_pts = np.array([
                            [cx - 12, cy + box_half_h - 2],
                            [cx + 12, cy + box_half_h - 2],
                            [cx + int(np.clip(dx * 0.3, -35, 35)), cy + box_half_h + 28]
                        ], dtype=np.int32)
                        cv2.fillPoly(tail_mask, [base_pts], 255)

                        aligned_bubble_mask = bubble_tool.reattach_tail(body_mask, tail_mask, tail_angle_deg)
                    else:
                        # Off-screen speaker: hide tail, use clean bubble body ONLY
                        aligned_bubble_mask = body_mask

                    # Draw white bubble fill and black contour stroke onto panel_bgr
                    bubble_contours, _ = cv2.findContours(aligned_bubble_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(panel_bgr, bubble_contours, -1, (255, 255, 255), -1)
                    cv2.drawContours(panel_bgr, bubble_contours, -1, (0, 0, 0), 3)

                    # Dilate placed bubble in total_person_mask so next speaker bubble avoids it
                    bubble_kernel = np.ones((22, 22), np.uint8)
                    dilated_bubble = cv2.dilate(aligned_bubble_mask, bubble_kernel)
                    total_person_mask[dilated_bubble > 0] = 255

                    # Typeset text strictly inside main ellipse body
                    pil_panel = Image.fromarray(cv2.cvtColor(panel_bgr, cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(pil_panel)

                    y_start = cy - (len(selected_lines) * selected_line_height) // 2
                    for line in selected_lines:
                        l_bbox = draw.textbbox((0, 0), line, font=selected_font)
                        text_w = l_bbox[2] - l_bbox[0]
                        draw.text((cx - text_w // 2, y_start), line, font=selected_font, fill=(0, 0, 0))
                        y_start += selected_line_height

                    panel_bgr = cv2.cvtColor(np.array(pil_panel), cv2.COLOR_RGB2BGR)
            except Exception as err:
                print(f"Warning: Bubble typesetting error for panel: {err}")

        # Paste panel onto main A4 page
        final_panel_pil = Image.fromarray(cv2.cvtColor(panel_bgr, cv2.COLOR_BGR2RGB))
        page.paste(final_panel_pil, (int(x), int(y)))
        draw_page.rectangle([int(x), int(y), int(x + w), int(y + h)], outline="black", width=2)

    return page

