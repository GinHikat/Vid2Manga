import cv2
import numpy as np
import random
import os
from Frame.manga_layout import *
from Frame.frame_processor import *

def main():
    img_path = 'Frame/images/output/layout_test_seed_42.jpg'
    
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found.")
        return
        
    img = cv2.imread(img_path)
    if img is None:
        print("Could not load image. Generating a blank one for testing.")
        img = np.ones((1400, 1000, 3), dtype=np.uint8) * 255

    # Retrieve frame coordinates
    frames = generate_manga_layout(width=1000, height=1400, num_frames=8, seed=42, margin=8)
    
    # We will draw on a copy of the image to visualize
    vis_img = img.copy()
    
    # Use a fixed seed for reproducibility of random persons
    np.random.seed(42)
    random.seed(42)

    for (fx, fy, fw, fh) in frames:
        # Generate random number of persons in this frame (1 or 2)
        num_persons = random.randint(1, 2)
        
        # Local mask for the frame containing characters (binary mask: 255=char, 0=bg)
        frame_char_mask = np.zeros((int(fh), int(fw)), dtype=np.uint8)
        
        persons = []
        for _ in range(num_persons):
            # person size
            pw = random.randint(int(fw*0.15), int(fw*0.35))
            ph = random.randint(int(fh*0.30), int(fh*0.70))
            
            # random person center within the frame, ensuring it is padded away from borders
            min_x = pw // 2 + 5
            max_x = max(min_x, int(fw) - pw // 2 - 5)
            px = random.randint(min_x, max_x)
            
            min_y = ph // 2 + 5
            max_y = max(min_y, int(fh) - ph // 2 - 5)
            py = random.randint(min_y, max_y)
            
            persons.append((px, py, pw, ph))
            
            # # draw person on local mask (using an ellipse to represent a person's head/body)
            # cv2.ellipse(frame_char_mask, (px, py), (pw//2, ph//2), 0, 0, 360, 255, -1)
            
            # # visualize person on the main image (Blue color = Person Placeholder)
            # cv2.ellipse(vis_img, (px + int(fx), py + int(fy)), (pw//2, ph//2), 0, 0, 360, (255, 0, 0), -1)

        # Let's generate a bubble for each person found in the frame
        for (px, py, pw, ph) in persons:
            # Randomize bubble size based on frame size
            bw = random.randint(int(fw*0.25), int(fw*0.45))
            bh = random.randint(int(fh*0.15), int(fh*0.25))
            
            # Create bubble mask for this frame, targeting proximity to this specific person
            bubble_mask, center_local = create_bubble_mask(
                image_shape=(int(fh), int(fw)), 
                axes=(bw, bh), 
                character_mask=frame_char_mask, 
                proximity_target=(px, py),
                num_persons=num_persons
            )
            
            # Add this generated bubble to the character mask so the next bubble avoids overlapping it too!
            frame_char_mask[bubble_mask > 0] = 255
            
            # Visualize bubble on main image
            cx, cy = center_local
            global_cx = cx + int(fx)
            global_cy = cy + int(fy)
            
            # Bubble in white with black border
            cv2.ellipse(vis_img, (global_cx, global_cy), (bw//2, bh//2), 0, 0, 360, (255, 255, 255), -1)
            cv2.ellipse(vis_img, (global_cx, global_cy), (bw//2, bh//2), 0, 0, 360, (0, 0, 0), 3)
            
    out_path = 'images/output/test_bubble_on_layout.jpg'
    cv2.imwrite(out_path, vis_img)
    print(f"Saved visualization to {out_path}")
