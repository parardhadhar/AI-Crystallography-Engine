import cv2
import torch
import os
import glob
import gc
from pathlib import Path
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
from physics_preprocess import preprocess_tem_image

def auto_label_dataset():
    print("Initializing Memory-Safe SAM Auto-Labeler...")
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    
    sam_checkpoint = str(base_dir / "weights" / "sam_vit_h_4b8939.pth")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    sam = sam_model_registry["vit_h"](checkpoint=sam_checkpoint)
    sam.to(device=device)

    # Use smaller points_per_side to save memory and processing time,
    # but still enough to capture defects
    mask_generator = SamAutomaticMaskGenerator(
        model=sam,
        points_per_side=16, 
        pred_iou_thresh=0.86,
        stability_score_thresh=0.92
    )

    for folder_name in ["train", "val"]:
        image_folder = str(base_dir / "tem_dataset" / "images" / folder_name)
        label_folder = str(base_dir / "tem_dataset" / "labels" / folder_name)
        os.makedirs(label_folder, exist_ok=True)

        image_paths = glob.glob(os.path.join(image_folder, "*.*"))
        print(f"Found {len(image_paths)} images to auto-label in {folder_name}.")

        for i, img_path in enumerate(image_paths):
            img_name = os.path.basename(img_path)
            print(f"[{i+1}/{len(image_paths)}] Auto-labeling {img_name}...")
            
            # 1. Physics Pre-Processing (SVD + CLAHE)
            # This flattens the background and pops the loops for SAM
            try:
                enhanced_image = preprocess_tem_image(img_path)
            except Exception as e:
                print(f"  -> Skipping due to error: {e}")
                continue
                
            image_rgb = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2RGB)
            img_h, img_w = enhanced_image.shape[:2]

            # 2. SAM Mask Generation
            masks = mask_generator.generate(image_rgb)
            
            # 3. Write YOLO labels
            txt_name = os.path.splitext(img_name)[0] + ".txt"
            txt_path = os.path.join(label_folder, txt_name)
            
            with open(txt_path, 'w') as f:
                for mask_dict in masks:
                    # bounding box is [x, y, w, h] in SAM format
                    bbox = mask_dict['bbox']
                    x, y, w, h = bbox
                    
                    # Convert to YOLO format [x_center, y_center, w, h] normalized
                    x_center = (x + w / 2) / img_w
                    y_center = (y + h / 2) / img_h
                    w_norm = w / img_w
                    h_norm = h / img_h
                    
                    # Prevent out-of-bounds boxes
                    x_center = max(0.0, min(1.0, x_center))
                    y_center = max(0.0, min(1.0, y_center))
                    w_norm = max(0.0, min(1.0, w_norm))
                    h_norm = max(0.0, min(1.0, h_norm))
                    
                    f.write(f"0 {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}\n")
            
            print(f"  -> Generated {len(masks)} labels for {img_name}")
            
            # 4. MEMORY MANAGEMENT (CRITICAL FIX FOR CRASH)
            del masks
            del image_rgb
            del enhanced_image
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

if __name__ == "__main__":
    auto_label_dataset()
