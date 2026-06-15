import cv2
import numpy as np

class AdvancedPostProcessor:
    """
    Solves Edge Cases in standard SAM outputs for Publication-Grade analysis:
    1. Particle Splitting (Over-segmentation): Merges nearby masks with continuous low gradients.
    2. Z-Contrast Overlapping: Uses Distance Transform and Watershed to gracefully de-blend 'snowman' shapes.
    """
    def __init__(self, gradient_threshold=50, merge_distance_px=5):
        self.grad_thresh = gradient_threshold
        self.merge_dist = merge_distance_px

    def merge_fractured_masks(self, masks, image_rgb):
        masks = [m for m in masks if m is not None]
        if not masks or len(masks) < 2:
            return masks

        h, w = image_rgb.shape[:2]
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        
        # Calculate Sobel gradient magnitude to judge boundary continuity
        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        grad_mag = cv2.magnitude(grad_x, grad_y)
        grad_mag = cv2.normalize(grad_mag, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
        boxes = [cv2.boundingRect(m) for m in masks]
        n = len(masks)
        adjacency = np.zeros((n, n), dtype=bool)
        
        bin_masks = []
        for m in masks:
            b = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(b, [m], -1, 255, -1)
            bin_masks.append(b)
            
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.merge_dist, self.merge_dist))

        # Check pairwise adjacency and continuous gradients
        for i in range(n):
            x1, y1, w1, h1 = boxes[i]
            dilated_i = cv2.dilate(bin_masks[i], kernel)
            
            for j in range(i + 1, n):
                x2, y2, w2, h2 = boxes[j]
                
                # Fast AABB intersection check before doing heavy pixel logic
                if not (x1 + w1 + self.merge_dist < x2 or x2 + w2 + self.merge_dist < x1 or 
                        y1 + h1 + self.merge_dist < y2 or y2 + h2 + self.merge_dist < y1):
                    
                    intersection = cv2.bitwise_and(dilated_i, bin_masks[j])
                    if np.any(intersection):
                        inter_mask = intersection > 0
                        avg_grad = np.mean(grad_mag[inter_mask])
                        
                        # Merge if the boundary gradient is lower than threshold
                        if avg_grad < self.grad_thresh:
                            adjacency[i, j] = True
                            adjacency[j, i] = True
                            
        # Connected components logic to fuse the graph
        visited = np.zeros(n, dtype=bool)
        merged_contours = []
        
        for i in range(n):
            if not visited[i]:
                cluster = [i]
                visited[i] = True
                queue = [i]
                while queue:
                    curr = queue.pop(0)
                    for neighbor in range(n):
                        if adjacency[curr, neighbor] and not visited[neighbor]:
                            visited[neighbor] = True
                            cluster.append(neighbor)
                            queue.append(neighbor)
                            
                unified_mask = np.zeros((h, w), dtype=np.uint8)
                for c_idx in cluster:
                    cv2.bitwise_or(unified_mask, bin_masks[c_idx], dst=unified_mask)
                    
                # Extract merged external contour
                cnts, _ = cv2.findContours(unified_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if cnts:
                    c = max(cnts, key=cv2.contourArea)
                    merged_contours.append(c)
                    
        return merged_contours

    def watershed_deblend(self, masks, image_rgb):
        if not masks:
            return []

        h, w = image_rgb.shape[:2]
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        final_contours = []
        
        for m in masks:
            area = cv2.contourArea(m)
            if area < 100: # Too small to split
                final_contours.append(m)
                continue
                
            mask_bin = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(mask_bin, [m], -1, 255, -1)
            
            # Compute topological Distance Transform
            dist_transform = cv2.distanceTransform(mask_bin, cv2.DIST_L2, 5)
            
            # Extract local maxima peaks (centers of overlapping particles)
            ret, sure_fg = cv2.threshold(dist_transform, 0.4 * dist_transform.max(), 255, 0)
            sure_fg = np.uint8(sure_fg)
            
            sure_bg = cv2.dilate(mask_bin, np.ones((3,3), np.uint8), iterations=1)
            unknown = cv2.subtract(sure_bg, sure_fg)
            
            ret, markers = cv2.connectedComponents(sure_fg)
            
            # If only 1 peak is found, it's a single valid defect. No split needed.
            if ret <= 2: 
                final_contours.append(m)
                continue
                
            markers = markers + 1
            markers[unknown == 255] = 0
            
            # Perform mathematically guided watershed separation using image gradients
            img_bgr = cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)
            markers = cv2.watershed(img_bgr, markers)
            
            for label_id in range(2, ret + 1):
                single_particle = np.zeros((h, w), dtype=np.uint8)
                single_particle[markers == label_id] = 255
                
                # Cleanup edge noise created by the watershed boundaries
                single_particle = cv2.morphologyEx(single_particle, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
                cnts, _ = cv2.findContours(single_particle, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if cnts:
                    c = max(cnts, key=cv2.contourArea)
                    if cv2.contourArea(c) > 20:
                        final_contours.append(c)
                        
        return final_contours

    def process(self, masks, image_rgb):
        """ Executes Option B: Strict Merge first, then elegant Watershed split """
        merged_masks = self.merge_fractured_masks(masks, image_rgb)
        deblended_masks = self.watershed_deblend(merged_masks, image_rgb)
        return deblended_masks
