import cv2
import numpy as np

class Bubble:
    """Utilities for processing and manipulating speech bubbles."""
    def __init__(self):
        pass

    def get_bubble_mask(self, image, background_is_white=True):
        """Extracts a binary mask of the speech bubble."""
        if isinstance(image, str):
            image = cv2.imread(image)
        if image is None:
            return np.array([])
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

    def segment_bubble(self, mask):
        """Segments bubble mask into body and tail using morphology."""
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

    def extract_biggest_polygon(self, mask, epsilon_factor=0.01):
        """Simplifies the largest contour into a polygon."""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        biggest_contour = max(contours, key=cv2.contourArea)
        epsilon = epsilon_factor * cv2.arcLength(biggest_contour, True)
        return cv2.approxPolyDP(biggest_contour, epsilon, True)

    def decompose_bubble(self, image):
        """Decomposes bubble into polygon body and tail mask."""
        mask = self.get_bubble_mask(image)
        if len(mask) == 0 or np.sum(mask) == 0:
            return None, None, None
        body_mask, tail_mask = self.segment_bubble(mask)
        body_polygon = self.extract_biggest_polygon(body_mask)
        return body_polygon, tail_mask, body_mask

    def reattach_tail(self, body_mask, tail_mask, angle_deg):
        """Reattaches the tail to the body at a specific angle."""
        def get_center(m):
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
