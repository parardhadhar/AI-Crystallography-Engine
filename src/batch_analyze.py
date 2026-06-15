import os
import glob
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from ultralytics import YOLO

# SAM imports
from segment_anything import sam_model_registry, SamPredictor
from physics_preprocess import preprocess_tem_image

def run_batch_analysis():
    print("Initializing Batch Analysis & Morphological Segregation Engine...")
    
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    
    # 1. Load Custom Phase 1 YOLO Model via SAHI
    weights_path = str(base_dir / "IISc_TEM_Research" / "yolo_baseline_v1-2" / "weights" / "best.pt")
    if not os.path.exists(weights_path):
        raise FileNotFoundError(f"Weights not found at {weights_path}")
    
    device_str = "cuda:0" if torch.cuda.is_available() else "cpu"
    
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    
    detection_model = AutoDetectionModel.from_pretrained(
        model_type='yolov8',
        model_path=weights_path,
        confidence_threshold=0.15,
        device=device_str,
    )
    
    # 2. Load SAM
    sam_path = str(base_dir / "weights" / "sam_vit_h_4b8939.pth")
    sam = sam_model_registry["vit_h"](checkpoint=sam_path)
    sam.to(device=device_str)
    sam_predictor = SamPredictor(sam)
    
    output_dir = base_dir / "data" / "output" / "batch_results"
    os.makedirs(output_dir, exist_ok=True)
    
    report_data = []

    # Get all images
    image_paths = []
    for folder in ["train", "val"]:
        image_paths.extend(glob.glob(str(base_dir / "tem_dataset" / "images" / folder / "*.*")))
        
    print(f"Found {len(image_paths)} images for batch analysis.")

    for i, img_path in enumerate(image_paths):
        img_name = os.path.basename(img_path)
        print(f"\n[{i+1}/{len(image_paths)}] Processing {img_name}...")
        
        # Physics Pre-Processing
        try:
            enhanced_image = preprocess_tem_image(img_path)
        except Exception as e:
            print(f"Skipping {img_name} due to error: {e}")
            continue
            
        image_rgb = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2RGB)
        
        # SAHI Sliced Inference
        result = get_sliced_prediction(
            image_rgb,
            detection_model,
            slice_height=512,
            slice_width=512,
            overlap_height_ratio=0.2,
            overlap_width_ratio=0.2
        )
        
        boxes = []
        for obj in result.object_prediction_list:
            bbox = obj.bbox.to_xyxy()
            
            # THE PHYSICAL PLAUSIBILITY FILTER (Solves the "Massive Blob")
            # Calculate width and height of the box
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            area = w * h
            
            # Nanoscale loops are tiny. If a box is massive (e.g., covering the whole screen)
            # or highly elongated (like a bend contour), we mathematically delete it.
            # Max area allowed: ~50,000 pixels (which is still a huge loop).
            # Max width/height allowed: 300 pixels
            if area < 50000 and w < 300 and h < 300:
                boxes.append(bbox)
            
        print(f" -> Found {len(boxes)} physically plausible loops using SAHI slicing (filtered out giant blobs).")
        
        if len(boxes) == 0:
            continue
            
        # SAM Segmentation & Morphological Analysis
        sam_predictor.set_image(image_rgb)
        
        small_loops = 0
        medium_loops = 0
        large_loops = 0
        
        plt.figure(figsize=(16, 16))
        plt.imshow(image_rgb)
        
        for box in boxes:
            box_np = np.array(box)
            masks, _, _ = sam_predictor.predict(box=box_np, multimask_output=False)
            mask = masks[0]
            
            # Calculate geometric properties
            area_pixels = np.sum(mask)
            
            # Segregation Logic (Area-based)
            # Thresholds are arbitrary and should be calibrated to nm scale if pixel scale is known
            if area_pixels < 500:
                small_loops += 1
                color = np.array([255/255, 50/255, 50/255, 0.5]) # Red for Small
            elif area_pixels < 2000:
                medium_loops += 1
                color = np.array([50/255, 255/255, 50/255, 0.5]) # Green for Medium
            else:
                large_loops += 1
                color = np.array([50/255, 50/255, 255/255, 0.5]) # Blue for Large
                
            # Shade the mask
            h, w = mask.shape[-2:]
            mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
            plt.gca().imshow(mask_image)
            plt.gca().contour(mask, levels=[0.5], colors=[color[:3]], linewidths=[1.5])
            
        # Save visualization
        plt.title(f"{img_name} - Loop Segregation\nSmall: {small_loops} | Medium: {medium_loops} | Large: {large_loops}", fontsize=18)
        plt.axis('off')
        out_img_path = str(output_dir / f"segregated_{img_name}")
        plt.savefig(out_img_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        # Log to report
        report_data.append({
            "Image": img_name,
            "Total Loops": len(boxes),
            "Small Loops (<500px)": small_loops,
            "Medium Loops (500-2000px)": medium_loops,
            "Large Loops (>2000px)": large_loops
        })
        
        print(f" -> Saved visualization to {out_img_path}")
        
    # Generate CSV Report
    if report_data:
        df = pd.DataFrame(report_data)
        csv_path = str(output_dir / "loop_segregation_report.csv")
        df.to_csv(csv_path, index=False)
        print(f"\nBatch Analysis Complete! Report saved to {csv_path}")

if __name__ == "__main__":
    run_batch_analysis()
