import os
import glob
import cv2
import torch
import numpy as np
from pathlib import Path
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction
from physics_preprocess import preprocess_tem_image

def is_valid_loop(bbox_pixels):
    """
    The Mathematical Heuristic Filter (Virtual Metallurgist).
    Checks if a bounding box contains a real dislocation loop strain field 
    or just a flat black speck of dirt.
    """
    # If box is entirely empty or 1 pixel, it's noise
    if bbox_pixels.size == 0 or bbox_pixels.shape[0] < 2 or bbox_pixels.shape[1] < 2:
        return False
        
    # Convert to grayscale for gradient analysis
    gray = cv2.cvtColor(bbox_pixels, cv2.COLOR_BGR2GRAY)
    
    # Calculate pixel intensity variance (Standard Deviation)
    std_dev = np.std(gray)
    
    # Real loops have strain fields (black rims, lighter centers), meaning HIGH variance.
    # Dirt is solid black, meaning VERY LOW variance.
    # 5.0 is a calibrated threshold for TEM dirt vs strain contrast.
    if std_dev < 5.0:
        return False
        
    return True

def run_autonomous_cleanse():
    print("Booting up the Virtual Metallurgist (Autonomous Dataset Cleanser)...")
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    
    # 1. Load Phase 1 Model via SAHI
    weights_path = str(base_dir / "IISc_TEM_Research" / "yolo_baseline_v1-2" / "weights" / "best.pt")
    device_str = "cuda:0" if torch.cuda.is_available() else "cpu"
    
    print(f"Loading Phase 1 SAHI Tracker from: {weights_path}")
    detection_model = AutoDetectionModel.from_pretrained(
        model_type='yolov8',
        model_path=weights_path,
        confidence_threshold=0.15,
        device=device_str,
    )
    
    total_images = 0
    total_pristine_labels = 0
    total_rejected = 0

    for folder_name in ["train", "val"]:
        image_folder = str(base_dir / "tem_dataset" / "images" / folder_name)
        label_folder = str(base_dir / "tem_dataset" / "labels" / folder_name)

        image_paths = glob.glob(os.path.join(image_folder, "*.*"))
        
        for i, img_path in enumerate(image_paths):
            img_name = os.path.basename(img_path)
            
            # Physics Pre-Processing
            try:
                enhanced_image = preprocess_tem_image(img_path)
            except Exception as e:
                print(f"Skipping {img_name}: {e}")
                continue
                
            image_rgb = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2RGB)
            img_h, img_w = enhanced_image.shape[:2]

            # SAHI Sliced Inference
            result = get_sliced_prediction(
                image_rgb,
                detection_model,
                slice_height=512,
                slice_width=512,
                overlap_height_ratio=0.2,
                overlap_width_ratio=0.2
            )
            
            valid_boxes = []
            
            for obj in result.object_prediction_list:
                bbox = obj.bbox.to_xyxy()
                x_min, y_min, x_max, y_max = map(int, bbox)
                
                # Clamp coordinates to image boundaries
                x_min = max(0, min(x_min, img_w - 1))
                y_min = max(0, min(y_min, img_h - 1))
                x_max = max(0, min(x_max, img_w))
                y_max = max(0, min(y_max, img_h))
                
                w = x_max - x_min
                h = y_max - y_min
                area = w * h
                
                # 1. GEOMETRIC FILTER (Remove massive blobs and bend contours)
                if area > 50000 or w > 300 or h > 300:
                    total_rejected += 1
                    continue
                    
                # 2. STRAIN FIELD GRADIENT FILTER (Remove flat dirt)
                bbox_pixels = image_rgb[y_min:y_max, x_min:x_max]
                if not is_valid_loop(bbox_pixels):
                    total_rejected += 1
                    continue
                    
                # Passed all physics heuristics!
                valid_boxes.append([x_min, y_min, x_max, y_max])
            
            # Overwrite the old messy YOLO labels with pristine mathematical labels
            txt_name = os.path.splitext(img_name)[0] + ".txt"
            txt_path = os.path.join(label_folder, txt_name)
            
            with open(txt_path, 'w') as f:
                for box in valid_boxes:
                    x_min, y_min, x_max, y_max = box
                    
                    x_center = ((x_min + x_max) / 2) / img_w
                    y_center = ((y_min + y_max) / 2) / img_h
                    w_norm = (x_max - x_min) / img_w
                    h_norm = (y_max - y_min) / img_h
                    
                    f.write(f"0 {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}\n")
                    total_pristine_labels += 1
                    
            total_images += 1
            print(f"[{total_images}] Cleaned {img_name} -> Kept: {len(valid_boxes)} pristine loops.")

    print("\n--- Autonomous Dataset Cleansing Complete ---")
    print(f"Total Images Processed: {total_images}")
    print(f"Total Pristine Loops Saved: {total_pristine_labels}")
    print(f"Total Hallucinations/Dirt Rejected by Physics Heuristics: {total_rejected}")
    print("Dataset is now ready for SOTA Phase 2 Training!")

if __name__ == "__main__":
    run_autonomous_cleanse()
