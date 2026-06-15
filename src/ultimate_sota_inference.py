import os
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction
from segment_anything import sam_model_registry, SamPredictor
from physics_preprocess import preprocess_tem_image

def generate_ultimate_presentation():
    print("Initializing Ultimate SOTA Inference Engine...")
    
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    
    # Target image for the presentation slide
    image_name = "tem13.jpg" # You can change this to any image
    image_path = str(base_dir / "data" / "input" / image_name)
    output_path = str(base_dir / "data" / "output" / f"ultimate_sota_{image_name}")
    
    # 1. Load the SOTA YOLO Model via SAHI
    # We point to the yolo_sota_master weights (Phase 2 model)
    weights_path = str(base_dir / "IISc_TEM_Research" / "yolo_sota_master" / "weights" / "best.pt")
    
    # Fallback to Phase 1 if Phase 2 isn't finished training yet
    if not os.path.exists(weights_path):
        print("SOTA Master weights not found (Training might still be running).")
        print("Falling back to Phase 1 Tracker for demonstration...")
        weights_path = str(base_dir / "IISc_TEM_Research" / "yolo_baseline_v1-2" / "weights" / "best.pt")
    
    device_str = "cuda:0" if torch.cuda.is_available() else "cpu"
    
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

    # 3. Physics Preprocessing
    print(f"Applying Physics SVD/CLAHE Preprocessing to {image_name}...")
    enhanced_image = preprocess_tem_image(image_path)
    image_rgb = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2RGB)
    
    # 4. SAHI Inference
    print("Running Sliced Autonomous Inference...")
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
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        area = w * h
        # Apply physical plausibility filter
        if area < 50000 and w < 300 and h < 300:
            boxes.append(bbox)
            
    print(f"Found {len(boxes)} physically verified loops.")
    
    if len(boxes) == 0:
        print("No loops found. Exiting.")
        return

    # 5. SAM Segmentation & Crystallographic Geometric Segregation
    print("Passing coordinates to SAM for pixel-perfect semantic rendering...")
    sam_predictor.set_image(image_rgb)
    
    plt.figure(figsize=(16, 16))
    
    # We will display the original RAW image for the slide (without CLAHE artifacts)
    raw_image = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)
    plt.imshow(raw_image)
    
    faulted_111 = 0
    perfect_110 = 0
    perfect_011 = 0
    
    for box in boxes:
        box_np = np.array(box)
        masks, _, _ = sam_predictor.predict(box=box_np, multimask_output=False)
        mask = masks[0]
        
        # Calculate Aspect Ratio of the Mask
        y_indices, x_indices = np.where(mask > 0)
        if len(x_indices) < 10:
            continue # Skip noise
            
        width = np.max(x_indices) - np.min(x_indices)
        height = np.max(y_indices) - np.min(y_indices)
        
        # Avoid division by zero
        if height == 0: height = 1
        aspect_ratio = min(width, height) / max(width, height)
        
        # Classify based on Table 1 (001 Zone Axis)
        # Faulted a/3<111> loops = 1:0.577 aspect ratio
        # Perfect a/2<110> loops = edge-on (very low aspect ratio, e.g. < 0.3)
        # Perfect a/2<011> loops = 1:0.707 aspect ratio
        
        if aspect_ratio < 0.35:
            perfect_110 += 1
            color = np.array([50/255, 50/255, 255/255, 0.6]) # Blue for Perfect 110 (Edge-on)
            label = "Perfect [110]"
        elif aspect_ratio < 0.64: # ~0.577
            faulted_111 += 1
            color = np.array([255/255, 50/255, 50/255, 0.6]) # Red for Faulted 111
            label = "Faulted [111]"
        else: # ~0.707 to 1.0
            perfect_011 += 1
            color = np.array([50/255, 255/255, 50/255, 0.6]) # Green for Perfect 011
            label = "Perfect [011]"
            
        h, w = mask.shape[-2:]
        mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
        plt.gca().imshow(mask_image)
        # Add a crisp border
        plt.gca().contour(mask, levels=[0.5], colors=[color[:3]], linewidths=[1.5])
        
    plt.title(f"Crystallographic Segmentation (001 Zone Axis)\nFaulted [111]: {faulted_111} | Perfect [110]: {perfect_110} | Perfect [011]: {perfect_011}", fontsize=22)
    plt.axis('off')
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=600, bbox_inches='tight')
    print(f"\nSaved Ultimate Checkmate Slide to: {output_path}")

if __name__ == "__main__":
    generate_ultimate_presentation()
