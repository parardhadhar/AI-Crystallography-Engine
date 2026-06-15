import os
import argparse
from pathlib import Path
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

def run_auto_mask(image_path: str, output_path: str, sam_checkpoint: str):
    print("Loading SAM...")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    sam = sam_model_registry["vit_h"](checkpoint=sam_checkpoint)
    sam.to(device=device)

    # Use the Automatic Mask Generator (Zero-Shot Grid Prompting)
    mask_generator = SamAutomaticMaskGenerator(
        model=sam,
        points_per_side=32, # Drops a 32x32 grid of points to find tiny loops
        pred_iou_thresh=0.86, # Only keep high-confidence shapes
        stability_score_thresh=0.92
    )

    print(f"Loading the TEM Image from {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not read {image_path}")
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    print("SAM is analyzing the grid... this may take a minute.")
    masks = mask_generator.generate(image_rgb)
    print(f"SAM found {len(masks)} distinct objects.")

    # Visualization
    plt.style.use('dark_background')
    plt.figure(figsize=(12, 12), facecolor='#0B1B3D')
    plt.imshow(image_rgb)

    # Overlay masks with random distinct colors so you can see separation
    for mask_dict in masks:
        mask = mask_dict['segmentation']
        color = np.concatenate([np.random.random(3), np.array([0.5])], axis=0) # Alpha 0.5
        h, w = mask.shape[-2:]
        mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
        plt.gca().imshow(mask_image)
        
        # also add contour for visual pop
        plt.gca().contour(mask, levels=[0.5], colors=[color[:3]], linewidths=[1])

    plt.title("Zero-Shot SAM Segmentation (No YOLO Pre-training)", fontsize=18, color='white', pad=15)
    plt.axis('off')
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='#0B1B3D')
    plt.close()
    print(f"Saved visualization to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="../data/input/tem13.jpg")
    parser.add_argument("--output", type=str, default="../data/output/tem13_auto_result.jpg")
    parser.add_argument("--sam_checkpoint", type=str, default="../weights/sam_vit_h_4b8939.pth")
    args = parser.parse_args()
    
    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)
    sam_checkpoint = os.path.abspath(args.sam_checkpoint)
    
    run_auto_mask(input_path, output_path, sam_checkpoint)
