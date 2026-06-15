import cv2
import numpy as np
from skimage.feature import blob_log

class MorphologyDetector:
    """
    The Mathematical Core of the Hybrid Pipeline.
    Deterministically locates physical strain fields of dislocation loops 
    using Morphological Black-Hat transforms and Laplacian of Gaussian (LoG).
    """
    def __init__(self, kernel_size=(35, 35), max_sigma=15, num_sigma=10, threshold=0.1, buffer=2, scale_nm_per_pixel=None):
        self.kernel_size = kernel_size
        self.max_sigma = max_sigma
        self.num_sigma = num_sigma
        self.threshold = threshold
        self.buffer = buffer
        self.scale_nm_per_pixel = scale_nm_per_pixel

    def get_bounding_boxes(self, image: np.ndarray, return_diameters=False) -> list:
        """
        Takes a raw TEM image (BGR or Grayscale array) and returns 
        a list of bounding boxes [x_min, y_min, x_max, y_max].
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 1. Morphological Black-Hat transform
        # Extracts dark defects against the varying bright background
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, self.kernel_size)
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
        
        # Normalize and blur to reduce camera noise
        blackhat_norm = cv2.normalize(blackhat, None, 0, 255, cv2.NORM_MINMAX)
        blurred = cv2.GaussianBlur(blackhat_norm, (3, 3), 0)

        # 2. Adaptive Thresholding
        # Replaces global Otsu, which often groups large background variations together.
        # Adaptive thresholding isolates small, sharp dark features (the loops) and ignores global gradients.
        
        # Sensitivity UI (0.1 - 1.0): Map to a constant C subtraction
        # In cv2.adaptiveThreshold, Threshold = local_mean - C.
        # Since blackhat makes loops bright, we want Threshold = local_mean + X (so C = -X).
        # Sensitivity 0.1 (Strict) -> X = 30 -> C = -30 (only detects very strong/dark loops)
        # Sensitivity 1.0 (Highly Sensitive) -> X = 5 -> C = -5 (detects faint loops)
        c_val = -30.0 + (self.threshold - 0.1) * (25.0 / 0.9)
        
        # We look for features that are BRIGHTER than the local mean in the blackhat image.
        # The block size MUST be physically larger than the largest expected loop, 
        # otherwise the local mean is dominated by the loop itself.
        # A loop is typically max 100nm. We set block size to ~150nm in pixels.
        block_size = 91
        if self.scale_nm_per_pixel and self.scale_nm_per_pixel > 0:
            block_size = int(150.0 / self.scale_nm_per_pixel)
            
        block_size = max(35, block_size)
        block_size = block_size | 1 # mathematically guarantee it is an odd number
        
        binary = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, block_size, c_val
        )

        # 3. Morphological Close to connect fragmented parts of single loops
        close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel)

        # 4. Find all objects
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes = []
        diameters = []
        height, width = gray.shape

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            
            # The true physical size of the loop is its longest dimension (major axis)
            major_axis_px = max(w, h)
            
            # Filter noise specks (< 3px)
            if major_axis_px < 3:
                continue

            diameter_nm = 0.0
            if self.scale_nm_per_pixel is not None:
                diameter_nm = major_axis_px * self.scale_nm_per_pixel
                # Physics Rule: The ENTIRE loop length must be >= 3nm.
                if diameter_nm < 3.0:
                    continue
                # Relaxed size limit to 300nm to account for UI scale input errors
                if diameter_nm > 300.0:
                    continue
            else:
                # If no scale provided, assume loops shouldn't be larger than 15% of the image size
                if major_axis_px > max(width, height) * 0.15:
                    continue

            # Add context padding for SAM (SAM needs to see the background to segment well)
            pad = int(max(5, min(major_axis_px * 0.2, 15)))
            
            x_min = max(0, x - pad)
            y_min = max(0, y - pad)
            x_max = min(width, x + w + pad)
            y_max = min(height, y + h + pad)

            if x_max > x_min and y_max > y_min:
                boxes.append([x_min, y_min, x_max, y_max])
                diameters.append(diameter_nm)

        print(f"[Math Core] Generated {len(boxes)} high-quality region proposals for SAM.")

        if return_diameters:
            return boxes, diameters
        return boxes

if __name__ == "__main__":
    detector = MorphologyDetector()
    print("MorphologyDetector initialized successfully.")
