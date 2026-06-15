import os
import cv2
import numpy as np
from ultralytics import YOLO

class YOLODetector:
    def __init__(self, model_path: str, conf_threshold: float = 0.25):
        """
        Initializes the YOLOv8 detector using pre-trained weights (e.g. PANDA model_b.pt)
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"YOLO weights not found at {model_path}")
            
        print(f"Loading YOLO model from {model_path}...")
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold

    def get_bounding_boxes(self, image: np.ndarray, return_diameters=True):
        """
        Detects loops in the image and returns bounding boxes.
        Returns:
            boxes: list of [x_min, y_min, x_max, y_max]
            diameters: list of approximate diameters in pixels
        """
        # Run inference
        results = self.model.predict(
            source=image, 
            conf=self.conf_threshold, 
            verbose=False,
            device='0' # try GPU if available
        )
        
        boxes_out = []
        diameters_out = []
        
        if len(results) > 0:
            result = results[0]
            # YOLO boxes are in [x1, y1, x2, y2] format natively
            boxes = result.boxes.xyxy.cpu().numpy()
            
            for box in boxes:
                x1, y1, x2, y2 = map(int, box)
                boxes_out.append([x1, y1, x2, y2])
                
                # Approximate diameter as the average of width and height
                w = x2 - x1
                h = y2 - y1
                diameters_out.append((w + h) / 2.0)
                
        if return_diameters:
            return boxes_out, diameters_out
        return boxes_out
