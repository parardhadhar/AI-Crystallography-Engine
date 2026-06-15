import os
import glob
import cv2
import torch
from pathlib import Path
from ultralytics import YOLO
from physics_preprocess import preprocess_tem_image

def relabel_dataset():
    print("Initializing Phase 2 Relabeling Pipeline...")
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    
    # 1. Find the best Phase 1 YOLO Model
    project_dir = base_dir / "IISc_TEM_Research"
    weight_paths = list(project_dir.glob("yolo_baseline_v1*/weights/best.pt"))
    if not weight_paths:
        raise FileNotFoundError("Could not find any Phase 1 trained weights!")
        
    weight_paths.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    weights_path = str(weight_paths[0])
    print(f"Loading Phase 1 weights from: {weights_path}")
    
    yolo_model = YOLO(weights_path)
    
    # We use a confidence threshold of 0.15. This is low enough to catch true loops,
    # but high enough to completely ignore the dirt and artifacts SAM got confused by.
    CONFIDENCE_THRESHOLD = 0.15 
    
    total_new_labels = 0

    for folder_name in ["train", "val"]:
        image_folder = str(base_dir / "tem_dataset" / "images" / folder_name)
        label_folder = str(base_dir / "tem_dataset" / "labels" / folder_name)

        image_paths = glob.glob(os.path.join(image_folder, "*.*"))
        print(f"Phase 2: Relabeling {len(image_paths)} images in {folder_name}...")

        for i, img_path in enumerate(image_paths):
            img_name = os.path.basename(img_path)
            
            # Physics Pre-Processing (SVD + CLAHE)
            try:
                enhanced_image = preprocess_tem_image(img_path)
            except Exception as e:
                print(f"  -> Skipping {img_name} due to error: {e}")
                continue
                
            image_rgb = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2RGB)
            img_h, img_w = enhanced_image.shape[:2]

            # Run Phase 1 YOLO Model Inference
            results = yolo_model.predict(image_rgb, conf=CONFIDENCE_THRESHOLD, verbose=False)
            
            # Write new pristine YOLO labels (OVERWRITING the messy SAM labels)
            txt_name = os.path.splitext(img_name)[0] + ".txt"
            txt_path = os.path.join(label_folder, txt_name)
            
            # Overwrite mode
            with open(txt_path, 'w') as f:
                if len(results) > 0 and len(results[0].boxes) > 0:
                    boxes = results[0].boxes.xyxy.cpu().numpy().tolist()
                    for box in boxes:
                        x_min, y_min, x_max, y_max = box
                        
                        # Convert back to YOLO normalized center format
                        x_center = ((x_min + x_max) / 2) / img_w
                        y_center = ((y_min + y_max) / 2) / img_h
                        w_norm = (x_max - x_min) / img_w
                        h_norm = (y_max - y_min) / img_h
                        
                        # Prevent out-of-bounds
                        x_center = max(0.0, min(1.0, x_center))
                        y_center = max(0.0, min(1.0, y_center))
                        w_norm = max(0.0, min(1.0, w_norm))
                        h_norm = max(0.0, min(1.0, h_norm))
                        
                        f.write(f"0 {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}\n")
                        total_new_labels += 1
                        
            print(f"[{i+1}/{len(image_paths)}] Relabeled {img_name}: Found {len(results[0].boxes) if len(results) > 0 else 0} true loops.")
            
    print(f"Phase 2 Relabeling Complete! Generated {total_new_labels} pristine bounding boxes.")

if __name__ == "__main__":
    relabel_dataset()
