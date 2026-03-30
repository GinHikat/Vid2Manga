import cv2
import numpy as np
import os

class Bubble:
    def __init__(self):
        pass

    def get_bubble_mask(self, image, background_is_white=True):
        """
        Get a binary mask of the speech bubble from an image.
        """

        if isinstance(image, str):
            image = cv2.imread(image)
        
        if image is None:
            return np.array([])

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        if background_is_white:
            _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        else:
            _, binary = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)
            
        # Find contours and fill to get the full bubble shape
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask = np.zeros_like(binary)
        if contours:
            # Take the largest contour as the bubble
            main_contour = max(contours, key=cv2.contourArea)
            cv2.drawContours(mask, [main_contour], -1, 255, -1)
        return mask

    def segment_bubble(self, mask):
        """
        Segments a bubble mask into body and tail using Distance Transform and Opening logic.
        """
        dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        max_val = np.max(dist_transform)
        
        # Opening with kernel size 0.5 * max_dist
        kernel_size = int(max_val * 0.5) 
        if kernel_size < 3: kernel_size = 3
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        
        body_mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Smooth the body mask slightly
        body_mask = cv2.dilate(body_mask, np.ones((3,3), np.uint8))
        
        # Ensure it stays within the original mask
        body_mask = cv2.bitwise_and(body_mask, mask)
        
        tail_mask = cv2.subtract(mask, body_mask)

        # Clean up
        tail_mask = cv2.morphologyEx(tail_mask, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
        
        return body_mask, tail_mask

    def extract_biggest_polygon(self, mask, epsilon_factor=0.01):
        """
        Extracts the largest contour from the mask and simplifies it into a polygon.
        """
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
            
        # Get the biggest contour by area
        biggest_contour = max(contours, key=cv2.contourArea)
        
        # Approximate the contour to a polygon
        epsilon = epsilon_factor * cv2.arcLength(biggest_contour, True)
        polygon = cv2.approxPolyDP(biggest_contour, epsilon, True)
        
        return polygon

    def decompose_bubble(self, image):
        """
        Decomposes a bubble image into its parts using the polygon extractor for the body.
        Returns: (body_polygon, tail_mask, body_mask)
        """
        mask = self.get_bubble_mask(image)

        if len(mask) == 0 or np.sum(mask) == 0:
            return None, None, None
            
        body_mask, tail_mask = self.segment_bubble(mask)
        
        # Extract the biggest polygon as the main bubble body
        body_polygon = self.extract_biggest_polygon(body_mask)
                
        return body_polygon, tail_mask, body_mask

    def reattach_tail(self, body_mask, tail_mask, angle_deg):
        """
        Reattaches the tail to the bubble body at a new angle.
        
        Args:
            body_mask: Mask of the bubble body.
            tail_mask: Original tail mask.
            angle_deg: Target angle in degrees (0 = right, 90 = bottom, 180 = left, 270 = top).
            
        Returns:
            A combined binary mask with the tail moved to the new position.
        """
        # Find the centers
        M_body = cv2.moments(body_mask)
        if M_body["m00"] == 0:
            return body_mask
        bcx, bcy = int(M_body["m10"] / M_body["m00"]), int(M_body["m01"] / M_body["m00"])

        M_tail = cv2.moments(tail_mask)
        if M_tail["m00"] == 0:
            return body_mask
        tcx, tcy = int(M_tail["m10"] / M_tail["m00"]), int(M_tail["m01"] / M_tail["m00"])

        # Determine Original Vector
        # We find the angle the original tail was pointing relative to the center
        orig_angle_rad = np.arctan2(tcy - bcy, tcx - bcx)
        # Target angle in Rad - we use clockwise positive as OpenCV default
        target_angle_rad = np.deg2rad(angle_deg)
        
        # Rotate the tail mask around the body center
        # rotation angle is target - original (degrees clockwise)
        rot_angle_deg = np.rad2deg(target_angle_rad - orig_angle_rad)
        
        h, w = body_mask.shape[:2]
        # Rotate about the body's center
        # NOTE: cv2.getRotationMatrix2D takes anti-clockwise degrees
        rot_matrix = cv2.getRotationMatrix2D((bcx, bcy), -rot_angle_deg, 1.0)
        
        # Warp the tail
        rotated_tail = cv2.warpAffine(tail_mask, rot_matrix, (w, h), flags=cv2.INTER_NEAREST)
        
        # --- Slide tail to touch the body boundary ---
        # Target direction vector
        rad = np.deg2rad(angle_deg)
        vx, vy = np.cos(rad), np.sin(rad)
        
        # Find the boundary distance of the body along the ray
        # We start from the center and move outwards
        max_dim = max(w, h)
        body_edge_dist = 0
        for r in range(0, max_dim): 
            px, py = int(bcx + r * vx), int(bcy + r * vy)
            if 0 <= px < w and 0 <= py < h:
                if body_mask[py, px] > 0:
                    body_edge_dist = r
            else:
                break
        
        # Find the nearest point of the rotated tail along the ray (the "base" of the tail)
        tail_start_dist = -1
        for r in range(0, max_dim):
            px, py = int(bcx + r * vx), int(bcy + r * vy)
            if 0 <= px < w and 0 <= py < h:
                if rotated_tail[py, px] > 0:
                    tail_start_dist = r
                    break
            else:
                break
        
        final_tail = rotated_tail
        if tail_start_dist != -1:
            # Shift the tail so that tail_start_dist matches body_edge_dist
            # We add a small overlap (2 pixels) for better visual connection
            shift = (body_edge_dist - tail_start_dist) + 2
            
            shift_matrix = np.float32([[1, 0, shift * vx], [0, 1, shift * vy]])
            final_tail = cv2.warpAffine(rotated_tail, shift_matrix, (w, h), flags=cv2.INTER_NEAREST)

        return cv2.bitwise_or(body_mask, final_tail)



