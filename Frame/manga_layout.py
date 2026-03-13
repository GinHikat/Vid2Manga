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

def create_bubble_mask(image_shape, axes, character_mask=None, proximity_target=None, num_persons=1):
    """
    Generates a binary segmentation mask for an oval speech bubble.
    If character_mask is provided, finds the optimal position that avoids characters.
    
    Args:
        image_shape: (height, width) or (height, width, channels) of the frame.
        axes: (width, height) specifying the full width and height of the oval bubble.
        character_mask: A binary mask (H, W) where 255 indicates characters and 0 is background.
        proximity_target: Optional (x, y) tuple. If provided, penalizes positions farther from this target 
                          to keep the bubble as close to the target as possible without overlapping the character.
        num_persons: Optional int. The number of people in the frame. Used to adjust distance penalties 
                     so bubbles from multiple people don't fight too heavily for non-character space.
        
    Returns:
        final_mask: (H, W) binary mask of the placed bubble (255 for bubble, 0 for background).
        center: (x, y) chosen center of the bubble.
    """
    h, w = image_shape[:2]
    bw, bh = axes
    
    # base ellipse mask (bounding box size)
    # The bounding box of the ellipse is exactly (bw, bh)
    bubble_template = np.zeros((bh, bw), dtype=np.uint8)
    # cv2.ellipse needs center (x,y) and axes (half_width, half_height)
    cv2.ellipse(bubble_template, (bw // 2, bh // 2), (bw // 2, bh // 2), 0, 0, 360, 255, -1)
    
    if character_mask is not None:
        # character_mask should be uint8, 255 for character, 0 for background
        # Ensure mask is binary and uint8
        character_mask = (character_mask > 0).astype(np.uint8) * 255
        
        # Use matchTemplate to calculate the overlap between the character mask and the bubble template
        # cv2.TM_CCORR computes the sum of the element-wise multiplication of template and image
        # which effectively counts how many white pixels overlap.
        overlap_map = cv2.matchTemplate(character_mask, bubble_template, cv2.TM_CCORR)
        
        # Apply a distance penalty to keep the bubble close to the proximity_target
        if proximity_target is not None:
            px, py = proximity_target
            # Create a coordinate grid mapping the overlapping centers
            xs = np.arange(overlap_map.shape[1]) + bw // 2
            ys = np.arange(overlap_map.shape[0]) + bh // 2
            xv, yv = np.meshgrid(xs, ys)
            
            # Calculate Euclidean distance from each center to the target
            dist = np.sqrt((xv - px)**2 + (yv - py)**2)
            
            # The penalty weight should balance between avoiding character overlap and staying close to the person.
            # Base penalty weight on the number of people to allow more overlap in crowded frames 
            # while keeping bubbles next to the speaker.
            penalty_weight = (255.0 * bw * bh) * (0.005 / max(1, num_persons)) 
            penalty_map = dist * penalty_weight
            
            # Constrain bubbles to stay within the frame boundaries (don't get clipped)
            # This is done by adding a massive infinite penalty to edge positions
            pad_x = bw // 2 + 5
            pad_y = bh // 2 + 5
            
            # Penalize Left and Right boundaries
            if pad_x < overlap_map.shape[1]:
                overlap_map[:, :pad_x] += float('inf')
                overlap_map[:, -pad_x:] += float('inf')
            # Penalize Top and Bottom boundaries
            if pad_y < overlap_map.shape[0]:
                overlap_map[:pad_y, :] += float('inf')
                overlap_map[-pad_y:, :] += float('inf')
                
            overlap_map += penalty_map.astype(np.float32)
            
        # Find the position with the minimum overlap
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(overlap_map)
        
        # min_loc is (x, y) of the top-left corner of the template
        top_left_x, top_left_y = min_loc
        center_x = top_left_x + bw // 2
        center_y = top_left_y + bh // 2
    else:
        # Default to center-top of the image if no mask is provided
        center_x = w // 2
        center_y = h // 4
        
    # Generate the final mask in the full image size
    final_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.ellipse(final_mask, (center_x, center_y), (bw // 2, bh // 2), 0, 0, 360, 255, -1)
    
    return final_mask, (center_x, center_y)