import os
import glob
import cv2
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from morphology_detector import MorphologyDetector
from sam_segmenter import SAMSegmenter

def parse_args():
    parser = argparse.ArgumentParser(description="Deterministic Math-to-AI Hybrid Pipeline Execution")
    parser.add_argument(
        "--scale_nm_per_pixel", 
        type=float, 
        default=None, 
        help="Optional scale to mathematically convert pixel area to nanometers squared."
    )
    return parser.parse_args()

def execute_pipeline(scale_nm_per_pixel):
    print("==================================================")
    print("Booting Deterministic Math-to-AI Hybrid Pipeline")
    print("==================================================")

    # Resolve dynamic paths
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    
    input_dir = base_dir / "data" / "input"
    output_dir = base_dir / "data" / "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize Core Components
    math_core = MorphologyDetector(kernel_size=(35, 35), max_sigma=15, num_sigma=10, threshold=0.1, buffer=2)
    ai_core = SAMSegmenter()

    report_data = []
    image_paths = glob.glob(str(input_dir / "*.*"))

    if not image_paths:
        print(f"No images found in {input_dir}. Please place TEM images there and run again.")
        return

    for img_path in image_paths:
        img_name = os.path.basename(img_path)
        print(f"\nProcessing: {img_name}")
        
        # Load Image
        image_bgr = cv2.imread(img_path)
        if image_bgr is None:
            print(f"Failed to read {img_name}, skipping.")
            continue
            
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        # 1. Mathematical Morphology Phase
        # Deterministically extract tight bounding boxes via Black-Hat + LoG
        boxes = math_core.get_bounding_boxes(image_bgr)
        print(f" -> Mathematical Core found {len(boxes)} physical strain fields.")

        # 2. AI Handshake Phase
        # Generate pixel-perfect instance masks from deterministic boxes
        masks = ai_core.generate_masks(image_rgb, boxes)

        # 3. Quantification Phase
        areas = []
        for mask in masks:
            # Area in pixels is simply the sum of True values in the boolean mask
            area_pixels = np.sum(mask)
            
            # Mathematical conversion to Physical Area (nm^2) if scale is provided
            if scale_nm_per_pixel is not None:
                area_val = area_pixels * (scale_nm_per_pixel ** 2)
            else:
                area_val = area_pixels
                
            areas.append(round(area_val, 2))

        # Compile data for the CSV report
        report_data.append({
            "Image_Name": img_name,
            "Total_Defects_Found": len(boxes),
            "Defect_Areas": str(areas)
        })

        # 4. Visualization Export Phase
        plt.figure(figsize=(12, 12))
        plt.imshow(image_rgb)
        ax = plt.gca()

        # Pre-allocate a single composite mask array to prevent memory overflow (OOM)
        h, w = image_rgb.shape[:2]
        composite_mask = np.zeros((h, w, 4), dtype=np.float32)
        green_color = np.array([50/255, 255/255, 50/255, 0.6])
        
        for mask in masks:
            # Add to the composite mask wherever the individual mask is True
            composite_mask[mask] = green_color
            
        # Render the composite mask instantly with a single imshow call
        ax.imshow(composite_mask)
        
        # Now draw the lightweight bounding box lines
        for box in boxes:
            
            # Draw Red Mathematical Bounding Box
            x_min, y_min, x_max, y_max = box
            rect = plt.Rectangle(
                (x_min, y_min), 
                x_max - x_min, 
                y_max - y_min, 
                fill=False, 
                edgecolor='red', 
                linewidth=1.5
            )
            ax.add_patch(rect)

        unit = "nm²" if scale_nm_per_pixel else "pixels"
        plt.title(f"{img_name} - {len(boxes)} Defects Quantified ({unit})", fontsize=18)
        plt.axis('off')
        
        out_img_path = str(output_dir / f"math_ai_hybrid_{img_name}")
        plt.savefig(out_img_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f" -> Exported visualization to {out_img_path}")

    # Export Mathematical Quantification Report
    if report_data:
        csv_path = str(output_dir / "math_pipeline_report.csv")
        df = pd.DataFrame(report_data)
        df.to_csv(csv_path, index=False)
        print(f"\n==================================================")
        print(f"Pipeline Complete! Report exported to: {csv_path}")
        print("==================================================")

if __name__ == "__main__":
    args = parse_args()
    execute_pipeline(args.scale_nm_per_pixel)
