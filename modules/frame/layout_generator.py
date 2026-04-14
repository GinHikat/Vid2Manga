import random
import numpy as np
import cv2
from PIL import Image, ImageOps

def generate_manga_layout(width=1000, height=1400, num_frames=8, seed=None, std_dev=0.1, margin=10, min_ratio=0.3):
    """Generates ordered rectangular frames using a recursive splitting tree."""
    if seed is not None: random.seed(seed)
    root = {"rect": (0, 0, width, height), "left": None, "right": None}
    leaves = [root]
    
    while len(leaves) < num_frames:
        # Find leaf to split (prioritize large/extreme aspect ratios)
        best_idx, max_score = 0, 0
        for i, node in enumerate(leaves):
            _, _, w, h = node["rect"]
            score = (w * h) * (max(w/h, h/w) ** 1.5)
            if score > max_score: max_score, best_idx = score, i
                
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
    
    return [(x+margin, y+margin, w-2*margin, h-2*margin) if w>2*margin and h>2*margin else (x,y,w,h) 
            for (x,y,w,h) in _get_rects(root)]

def create_manga_page(images, frames, width=1000, height=1400, bg_color="white"):
    """Composites images into the generated layout using Pillow."""
    if len(images) != len(frames): raise ValueError("Mismatch between images and frames count")
    page = Image.new("RGB", (width, height), bg_color)
    for img_input, (x, y, w, h) in zip(images, frames):
        img = Image.open(img_input) if isinstance(img_input, str) else img_input.copy()
        page.paste(ImageOps.fit(img.convert('RGB'), (int(w), int(h)), method=Image.Resampling.LANCZOS), (int(x), int(y)))
    return page

def create_bubble_mask(image_shape, axes, character_mask=None, proximity_target=None, num_persons=1):
    """Finds optimal placement for an oval bubble, avoiding character overlap."""
    h, w = image_shape[:2]
    bw, bh = axes
    template = np.zeros((bh, bw), dtype=np.uint8)
    cv2.ellipse(template, (bw//2, bh//2), (bw//2, bh//2), 0, 0, 360, 255, -1)
    
    if character_mask is not None:
        char_m = (character_mask > 0).astype(np.uint8) * 255
        overlap_map = cv2.matchTemplate(char_m, template, cv2.TM_CCORR)
        
        if proximity_target:
            px, py = proximity_target
            xs, ys = np.arange(overlap_map.shape[1]) + bw//2, np.arange(overlap_map.shape[0]) + bh//2
            xv, yv = np.meshgrid(xs, ys)
            dist = np.sqrt((xv - px)**2 + (yv - py)**2)
            penalty = dist * (255.0 * bw * bh) * (0.005 / max(1, num_persons))
            # Boundary constraints
            pad_x, pad_y = bw//2 + 5, bh//2 + 5
            if pad_x < overlap_map.shape[1]: overlap_map[:, :pad_x] = overlap_map[:, -pad_x:] = float('inf')
            if pad_y < overlap_map.shape[0]: overlap_map[:pad_y, :] = overlap_map[-pad_y:, :] = float('inf')
            overlap_map += penalty.astype(np.float32)
            
        _, _, min_loc, _ = cv2.minMaxLoc(overlap_map)
        cx, cy = min_loc[0] + bw//2, min_loc[1] + bh//2
    else:
        cx, cy = w // 2, h // 4
        
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.ellipse(mask, (cx, cy), (bw//2, bh//2), 0, 0, 360, 255, -1)
    return mask, (cx, cy)
