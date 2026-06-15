import os
import cv2
import torch
import numpy as np
from segment_anything import sam_model_registry, SamPredictor

class SAMSegmenter:
    """
    AI Segmentation Core.
    Loads the Meta Segment Anything Model (SAM) to draw pixel-perfect 
    organic boundaries around the dislocation loops instead of square bounding boxes.
    """
    def __init__(self, checkpoint_path=None):
        if not checkpoint_path:
            import sys
            if getattr(sys, 'frozen', False):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            checkpoint_path = os.path.join(base_dir, "weights", "sam_vit_h_4b8939.pth")
            
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Initializing SAM Segmenter using checkpoint: {checkpoint_path}")
        
        try:
            self.sam = sam_model_registry["vit_h"](checkpoint=checkpoint_path)
            self.sam.to(device=device)
            self.predictor = SamPredictor(self.sam)
            print(f"SAM successfully loaded on {device.upper()}.")
        except Exception as e:
            print(f"Failed to load SAM: {e}")
            self.predictor = None

    def generate_masks(self, image_rgb, bounding_boxes):
        """
        Takes an RGB image and a list of bounding boxes [x_min, y_min, x_max, y_max].
        Returns a list of contours.
        """
        if not self.predictor:
            print("SAM predictor not available. Returning empty masks.")
            return [np.zeros(image_rgb.shape[:2], dtype=bool) for _ in bounding_boxes]

        self.predictor.set_image(image_rgb)
        
        all_masks = []
        for box in bounding_boxes:
            # Format expected by SAM: [x_min, y_min, x_max, y_max]
            input_box = np.array(box)
            
            masks, _, _ = self.predictor.predict(
                point_coords=None,
                point_labels=None,
                box=input_box[None, :],
                multimask_output=False,
            )
            
            # Convert immediately to contours to save massive amounts of RAM
            mask_uint8 = (masks[0] * 255).astype(np.uint8)
            contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if len(contours) > 0:
                # Keep the largest contour
                largest_contour = max(contours, key=cv2.contourArea)
                all_masks.append(largest_contour)
            else:
                all_masks.append(None)
            
        return all_masks
