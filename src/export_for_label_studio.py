import os
import glob
import cv2
import torch
from pathlib import Path
from ultralytics import YOLO
from physics_preprocess import preprocess_tem_image

def generate_label_studio_export():
    print("Generating Gold Standard AI Pre-Annotations for Label Studio...")
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    
    # 1. Load the pristine Phase 1 Model
    weights_path = str(base_dir / "IISc_TEM_Research" / "yolo_baseline_v1-2" / "weights" / "best.pt")
    if not os.path.exists(weights_path):
        raise FileNotFoundError(f"Phase 1 weights not found at {weights_path}")
        
    yolo_model = YOLO(weights_path)
    
    # We use a slightly lower confidence threshold (0.15) for the export.
    # It's better for the AI to over-predict slightly, so you can easily delete
    # false positives in Label Studio, rather than having to manually draw missing boxes.
    CONFIDENCE_THRESHOLD = 0.15 
    
    output_dir = base_dir / "data" / "label_studio_export"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(output_dir / "images", exist_ok=True)
    os.makedirs(output_dir / "labels", exist_ok=True)

    total_images = 0
    total_boxes = 0

    for folder_name in ["train", "val"]:
        image_folder = str(base_dir / "tem_dataset" / "images" / folder_name)
        image_paths = glob.glob(os.path.join(image_folder, "*.*"))

        for img_path in image_paths:
            img_name = os.path.basename(img_path)
            
            # Pre-process image
            try:
                enhanced_image = preprocess_tem_image(img_path)
            except Exception as e:
                print(f"Skipping {img_name}: {e}")
                continue
                
            image_rgb = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2RGB)
            img_h, img_w = enhanced_image.shape[:2]

            # Run Phase 1 Inference
            results = yolo_model.predict(image_rgb, conf=CONFIDENCE_THRESHOLD, verbose=False)
            
            # Save a copy of the raw image to the export folder for easy uploading
            raw_img = cv2.imread(img_path)
            cv2.imwrite(str(output_dir / "images" / img_name), raw_img)
            
            # Write YOLO labels
            txt_name = os.path.splitext(img_name)[0] + ".txt"
            txt_path = str(output_dir / "labels" / txt_name)
            
            with open(txt_path, 'w') as f:
                if len(results) > 0 and len(results[0].boxes) > 0:
                    boxes = results[0].boxes.xyxy.cpu().numpy().tolist()
                    for box in boxes:
                        x_min, y_min, x_max, y_max = box
                        
                        x_center = ((x_min + x_max) / 2) / img_w
                        y_center = ((y_min + y_max) / 2) / img_h
                        w_norm = (x_max - x_min) / img_w
                        h_norm = (y_max - y_min) / img_h
                        
                        f.write(f"0 {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}\n")
                        total_boxes += 1
            
            total_images += 1
            print(f"Processed {img_name}: exported {len(results[0].boxes) if len(results) > 0 else 0} labels.")
            
    print(f"\nExport Complete!")
    print(f"Copied {total_images} images to: {output_dir / 'images'}")
    print(f"Exported {total_boxes} YOLO labels to: {output_dir / 'labels'}")
    print("Ready to import into Label Studio!")

if __name__ == "__main__":
    generate_label_studio_export()
