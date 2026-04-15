import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

class Bubble:
    """Utilities for processing and manipulating speech bubbles."""
    
    def __init__(self):
        pass

    # --- Utilities ---

    def cv2_to_pil(self, cv2_image):
        """Converts OpenCV image (BGR or Gray) to PIL Image (RGB)."""
        if len(cv2_image.shape) == 2:
            return Image.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_GRAY2RGB))
        return Image.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB))

    def pil_to_cv2(self, pil_image):
        """Converts PIL Image (RGB) to OpenCV image (BGR)."""
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    # --- Bubble Extraction ---

    def get_bubble_mask(self, image, background_is_white=True):
        """Extracts a binary mask of the speech bubble.
        
        Args:
            image (str or np.ndarray): Path to image or image array.
            background_is_white (bool): Whether the background is white.
            
        Returns:
            np.ndarray: Binary mask of the bubble.
        """
        if isinstance(image, str):
            image = cv2.imread(image)
        if image is None:
            return np.array([], dtype=np.uint8)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        if background_is_white:
            _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        else:
            _, binary = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask = np.zeros_like(binary)
        if contours:
            main_contour = max(contours, key=cv2.contourArea)
            cv2.drawContours(mask, [main_contour], -1, 255, -1)
        return mask

    def clean_bubble(self, image):
        """Removes everything outside the main bubble border by padding with white.
        
        Args:
            image (str or np.ndarray): Input image path or array.
            
        Returns:
            np.ndarray: Image with background set to white.
        """
        if isinstance(image, str):
            img = cv2.imread(image)
        else:
            img = image
        if img is None:
            return np.array([], dtype=np.uint8)
        mask = self.get_bubble_mask(img)
        if mask.size == 0:
            return img
        result = img.copy()
        if len(img.shape) == 3:
            result[mask == 0] = [255, 255, 255]
        else:
            result[mask == 0] = 255
        return result

    # --- Typesetting ---

    def typeset_text(self, image, text, angle=None, tail_mask=None, font_path="arial.ttf", min_font_size=12, max_font_size=48, padding_erosion=5, max_frame_size=None):
        """Typesets text inside a bubble image by finding the optimal font size and line wrapping.
        Scales the bubble if necessary to fit the text.
        If angle is provided, reattaches the tail at that angle first.
        
        Args:
            image (str or np.ndarray): Input image path or array (the bubble body).
            text (str): String to typeset.
            angle (float, optional): Angle to reattach the tail.
            tail_mask (np.ndarray, optional): Mask of the tail to attach.
            font_path (str): Path to TTF font.
            min_font_size (int): Minimum font size.
            max_font_size (int): Maximum font size.
            padding_erosion (int): Erosion iterations to create a safe zone.
            max_frame_size (tuple): (W, H) limit for scaling the bubble.
            
        Returns:
            np.ndarray: Image with typeset text and properly attached tail.
        """
        if isinstance(image, str):
            image = cv2.imread(image)
        if image is None: return None

        # --- Bubble Assembly ---
        initial_mask = self.get_bubble_mask(image)
        body_mask, image_tail_mask = self.segment_bubble(initial_mask)
        
        target_typeset_mask = body_mask # Default to body for text
        current_img = image.copy()

        if angle is not None:
            # Use provided tail or try to extract from image
            used_tail = tail_mask if tail_mask is not None else image_tail_mask
            if used_tail is not None and used_tail.size > 0:
                # Reattach tail at new angle
                combined_mask = self.reattach_tail(body_mask, used_tail, angle)
                # Create a clean white canvas for the new bubble
                h, w = combined_mask.shape[:2]
                assembly = np.full((h, w,3), 255, dtype=np.uint8)
                # Draw bubble outline
                contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(assembly, contours, -1, (0, 0, 0), 2)
                current_img = assembly
                # Target for typesetting is still the body
                target_typeset_mask = body_mask

        words = text.split()
        
        def try_typesetting(img, text_words, fs, target_mask):
            kernel = np.ones((3, 3), np.uint8)
            safe_mask = cv2.erode(target_mask, kernel, iterations=padding_erosion)
            y_indices, _ = np.where(safe_mask > 0)
            if len(y_indices) == 0: return None, None

            min_y, max_y = np.min(y_indices), np.max(y_indices)
            center_y = (min_y + max_y) // 2
            
            try:
                font = ImageFont.truetype(font_path, fs)
            except:
                try:
                    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", fs)
                except:
                    font = ImageFont.load_default()

            temp_img = Image.new('RGB', (1, 1))
            draw = ImageDraw.Draw(temp_img)
            
            bbox = draw.textbbox((0, 0), "Ay", font=font)
            line_height = int((bbox[3] - bbox[1]) * 1.2)
            
            def get_lines(start_y):
                inner_lines = []
                current_line = []
                current_y = start_y
                
                for word in text_words:
                    test_line = " ".join(current_line + [word]) if current_line else word
                    test_w = draw.textbbox((0, 0), test_line, font=font)[2]
                    mid_y = current_y + line_height // 2
                    if mid_y >= safe_mask.shape[0]: return None
                    
                    row_pixels = np.where(safe_mask[mid_y, :] > 0)[0]
                    if len(row_pixels) < 2: return None
                    
                    available_w = row_pixels[-1] - row_pixels[0]
                    if test_w <= available_w:
                        current_line.append(word)
                    else:
                        if not current_line: return None 
                        inner_lines.append(" ".join(current_line))
                        current_line = [word]
                        current_y += line_height
                        if current_y + line_height > max_y: return None
                
                if current_line:
                    inner_lines.append(" ".join(current_line))
                
                if sum(len(l.split()) for l in inner_lines) < len(text_words): return None
                return inner_lines

            # Vertical fit search
            y_start_init = max(min_y, center_y - (len(text_words) // 3 * line_height) // 2)
            result_lines = get_lines(y_start_init)
            if not result_lines:
                for offset in range(-20, 21, 5):
                    result_lines = get_lines(y_start_init + offset)
                    if result_lines: break
            
            if result_lines:
                return result_lines, font
            return None, None

        # Scaling loop
        fit_lines = None
        fit_font = None
        
        while True:
            for fs in range(max_font_size, min_font_size - 1, -1):
                lines, font = try_typesetting(current_img, words, fs, target_typeset_mask)
                if lines:
                    fit_lines = lines
                    fit_font = font
                    break
            
            if fit_lines: break
            
            h, w = current_img.shape[:2]
            if max_frame_size and (w * 1.1 > max_frame_size[0] or h * 1.1 > max_frame_size[1]):
                break
            
            current_img = cv2.resize(current_img, (int(w * 1.1), int(h * 1.1)), interpolation=cv2.INTER_LINEAR)
            target_typeset_mask = cv2.resize(target_typeset_mask, (int(w * 1.1), int(h * 1.1)), interpolation=cv2.INTER_NEAREST)
            if current_img.shape[0] > 2000: break 

        if not fit_lines:
            print("Warning: Could not fit text in bubble.")
            return current_img

        # Render onto final assembled image
        pil_img = self.cv2_to_pil(current_img)
        kernel = np.ones((3, 3), np.uint8)
        safe_mask = cv2.erode(target_typeset_mask, kernel, iterations=padding_erosion)
        
        draw = ImageDraw.Draw(pil_img)
        bbox = draw.textbbox((0, 0), "Ay", font=fit_font)
        line_h = int((bbox[3] - bbox[1]) * 1.2)
        total_h = len(fit_lines) * line_h
        
        y_indices = np.where(safe_mask > 0)[0]
        min_y, max_y = np.min(y_indices), np.max(y_indices)
        y_cursor = (min_y + max_y) // 2 - total_h // 2
        
        for line in fit_lines:
            line_w = draw.textbbox((0, 0), line, font=fit_font)[2]
            mid_y = y_cursor + line_h // 2
            row_pixels = np.where(safe_mask[mid_y, :] > 0)[0]
            line_x = (row_pixels[0] + row_pixels[-1]) // 2 - line_w // 2 if len(row_pixels) > 0 else (pil_img.width - line_w) // 2
            draw.text((line_x, y_cursor), line, font=fit_font, fill=(0, 0, 0))
            y_cursor += line_h
            
        return self.pil_to_cv2(pil_img)

    # --- Bubble Segmentation ---

    def segment_bubble(self, mask):
        """Segments bubble mask into body and tail using morphology.
        
        Args:
            mask (np.ndarray): Binary mask of the bubble.
            
        Returns:
            tuple: (body_mask, tail_mask) as np.ndarray.
        """
        if mask is None or mask.size == 0:
            return None, None
        dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        max_val = np.max(dist_transform)
        kernel_size = max(3, int(max_val * 0.5))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        body_mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        body_mask = cv2.dilate(body_mask, np.ones((3,3), np.uint8))
        body_mask = cv2.bitwise_and(body_mask, mask)
        tail_mask = cv2.subtract(mask, body_mask)
        tail_mask = cv2.morphologyEx(tail_mask, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
        return body_mask, tail_mask

    # --- Geometric Analysis ---

    def extract_biggest_polygon(self, mask, epsilon_factor=0.01):
        """Simplifies the largest contour into a polygon.
        
        Args:
            mask (np.ndarray): Binary mask.
            epsilon_factor (float): Approximation accuracy.
            
        Returns:
            np.ndarray or None: Polygonal approximation of the contour.
        """
        if mask is None or mask.size == 0:
            return None
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        biggest_contour = max(contours, key=cv2.contourArea)
        epsilon = epsilon_factor * cv2.arcLength(biggest_contour, True)
        return cv2.approxPolyDP(biggest_contour, epsilon, True)

    # --- Decomposition Pipeline ---

    def decompose_bubble(self, image):
        """Decomposes bubble into polygon body and tail mask.
        
        Args:
            image (str or np.ndarray): Input image.
            
        Returns:
            tuple: (body_polygon, tail_mask, body_mask).
        """
        mask = self.get_bubble_mask(image)
        if mask is None or mask.size == 0 or np.sum(mask) == 0:
            return None, None, None
        body_mask, tail_mask = self.segment_bubble(mask)
        body_polygon = self.extract_biggest_polygon(body_mask)
        return body_polygon, tail_mask, body_mask

    # --- Alignment ---

    def calculate_relative_angle(self, from_mask, to_mask):
        """Calculates the angle from the centroid of one mask to another.
        
        Args:
            from_mask (np.ndarray): The source mask (e.g., bubble body).
            to_mask (np.ndarray): The target mask (e.g., character).
            
        Returns:
            float or None: Angle in degrees, pointing from from_mask to to_mask.
        """
        def get_center(m):
            if m is None or m.size == 0 or np.sum(m) == 0: return None
            moments = cv2.moments(m)
            if moments["m00"] == 0: return None
            return int(moments["m10"] / moments["m00"]), int(moments["m01"] / moments["m00"])

        c_from = get_center(from_mask)
        c_to = get_center(to_mask)
        
        if c_from is None or c_to is None:
            return None
            
        dx = c_to[0] - c_from[0]
        dy = c_to[1] - c_from[1]
        
        angle_rad = np.arctan2(dy, dx)
        return np.rad2deg(angle_rad)

    # --- Bubble Reattachment ---

    def reattach_tail(self, body_mask, tail_mask, angle_deg):
        """Reattaches the tail to the body at a specific angle.
        
        Args:
            body_mask (np.ndarray): Mask of the bubble body.
            tail_mask (np.ndarray): Mask of the bubble tail.
            angle_deg (float): Target angle in degrees.
            
        Returns:
            np.ndarray: Combined mask of body and rotated tail.
        """
        if body_mask is None or tail_mask is None:
            return body_mask if body_mask is not None else np.array([], dtype=np.uint8)

        def get_center(m):
            if m is None or m.size == 0: return None
            moments = cv2.moments(m)
            if moments["m00"] == 0: return None
            return int(moments["m10"] / moments["m00"]), int(moments["m01"] / moments["m00"])
            
        c_body = get_center(body_mask)
        c_tail = get_center(tail_mask)
        if not c_body or not c_tail: return body_mask
        
        bcx, bcy = c_body
        tcx, tcy = c_tail
        orig_angle = np.arctan2(tcy - bcy, tcx - bcx)
        target_angle = np.deg2rad(angle_deg)
        rot_angle_deg = np.rad2deg(target_angle - orig_angle)
        h, w = body_mask.shape[:2]
        rot_matrix = cv2.getRotationMatrix2D((bcx, bcy), -rot_angle_deg, 1.0)
        rotated_tail = cv2.warpAffine(tail_mask, rot_matrix, (w, h), flags=cv2.INTER_NEAREST)
        vx, vy = np.cos(target_angle), np.sin(target_angle)
        edge_dist = 0
        max_dim = max(w, h)
        for r in range(max_dim):
            px, py = int(bcx + r * vx), int(bcy + r * vy)
            if 0 <= px < w and 0 <= py < h and body_mask[py, px] > 0:
                edge_dist = r
            else: break
        tail_start = -1
        for r in range(max_dim):
            px, py = int(bcx + r * vx), int(bcy + r * vy)
            if 0 <= px < w and 0 <= py < h and rotated_tail[py, px] > 0:
                tail_start = r
                break
            elif px < 0 or px >= w or py < 0 or py >= h: break
        if tail_start != -1:
            shift = (edge_dist - tail_start) + 2
            sm = np.float32([[1, 0, shift * vx], [0, 1, shift * vy]])
            rotated_tail = cv2.warpAffine(rotated_tail, sm, (w, h), flags=cv2.INTER_NEAREST)
        return cv2.bitwise_or(body_mask, rotated_tail)
