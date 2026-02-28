import random
import math
from PIL import Image, ImageDraw, ImageOps

def generate_manga_layout(width = 1000, height = 1400, num_frames=8, seed=None, std_dev=0.1, margin=10, min_ratio=0.3):
    """
    Generates a list of rectangular frames for a manga page in a single function.
    Frames are correctly ordered top-to-bottom, left-to-right.
    Maintains balanced aspect ratios to avoid extreme vertical or horizontal frames.

    Input:
        width: width of the whole page (default is A4)
        height: height of the whole page
        num_frames: number of frames in the page
        seed: for reproducibility
        std_dev: frame splitting standard deviation, this creates a random frame size along different pages
        margin: the border between frames

    Output:
        list of frame coordinates (x_min, y_min, width, height)
    """
    if seed is not None:
        random.seed(seed)
        
    # We use a dictionary to represent nodes in our split tree
    # This allows us to maintain reading order without defining a separate class
    root = {"rect": (0, 0, width, height), "left": None, "right": None}
    leaves = [root]
    
    while len(leaves) < num_frames:
        largest_idx = 0
        max_score = 0
        
        # Pick leaf to split based on area AND aspect ratio 
        # to prevent extreme thin frames slipping through
        for i, node in enumerate(leaves):
            x, y, w, h = node["rect"]
            area = w * h
            
            # Max ratio between width and height (always >= 1)
            aspect = max(w / float(h), h / float(w))
            
            # Penalize extreme aspect ratios so they get prioritized for splitting
            score = area * (aspect ** 1.5)
            if score > max_score:
                max_score = score
                largest_idx = i
                
        node_to_split = leaves.pop(largest_idx)
        x, y, w, h = node_to_split["rect"]
        
        # Determine split direction strictly based on aspect ratio
        aspect_ratio = w / float(h)
        if aspect_ratio >= 1.25:
            # Much wider than tall, force vertical split (split the width into left/right)
            direction = 'vertical'
        elif aspect_ratio <= 0.8:
            # Much taller than wide, force horizontal split (split the height into top/bottom)
            direction = 'horizontal'
        else:
            direction = random.choice(['vertical', 'horizontal'])
            
        # Determine split percentages
        split_ratio = random.normalvariate(0.5, std_dev)
        split_ratio = max(min_ratio, min(1.0 - min_ratio, split_ratio))
        
        if direction == 'vertical':
            # Split the width -> yields Left and Right frames
            w1 = int(w * split_ratio)
            w2 = w - w1
            
            node_to_split["left"] = {"rect": (x, y, w1, h), "left": None, "right": None}
            node_to_split["right"] = {"rect": (x + w1, y, w2, h), "left": None, "right": None}
        else:
            # Split the height -> yields Top and Bottom frames
            h1 = int(h * split_ratio)
            h2 = h - h1
            
            node_to_split["left"] = {"rect": (x, y, w, h1), "left": None, "right": None}
            node_to_split["right"] = {"rect": (x, y + h1, w, h2), "left": None, "right": None}
            
        leaves.append(node_to_split["left"])
        leaves.append(node_to_split["right"])
        
    # Helper to traverse tree and get properly ordered frames (Top->Bottom, Left->Right)
    def _get_leaves(node):
        if node["left"] is None and node["right"] is None:
            return [node["rect"]]
        return _get_leaves(node["left"]) + _get_leaves(node["right"])
        
    ordered_rects = _get_leaves(root)
    
    # margins
    margin_frames = []
    for (x, y, w, h) in ordered_rects:
        if w > 2 * margin and h > 2 * margin:
            mx = x + margin
            my = y + margin
            mw = w - 2 * margin
            mh = h - 2 * margin
            margin_frames.append((mx, my, mw, mh))
        else:
            # Fallback if the space is too small for the requested margin
            margin_frames.append((x, y, w, h))
            
    return margin_frames

def create_manga_page(images, frames, width=1000, height=1400, bg_color="white"):
    """
    Takes a list of images (paths or PIL Image objects) and a list of frame coordinates,
    and resizes/crops each image to fit perfectly into its corresponding frame.
    
    Input:
        images: list of file paths or PIL Image objects (should be same length as frames)
        frames: list of (x, y, w, h) coordinates for the frames (from generate_manga_layout)
        width: width of the final manga page
        height: height of the final manga page
        bg_color: background color of the page
        
    Output:
        A PIL Image object representing the final generated manga page.
    """
    if len(images) != len(frames):
        raise ValueError(f"Number of images ({len(images)}) must match number of frames ({len(frames)})")

    # Create background page
    page = Image.new("RGB", (width, height), bg_color)
    
    for img_input, (x, y, w, h) in zip(images, frames):
        if isinstance(img_input, str):
            #if file path
            img = Image.open(img_input)
        else:
            img = img_input.copy()
            
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Fit the image into the target frame dimension (w, h)
        fitted_img = ImageOps.fit(img, (int(w), int(h)), method=Image.Resampling.LANCZOS)
        
        # Paste the image onto the main page at the correct coordinates
        page.paste(fitted_img, (int(x), int(y)))
        
    return page

