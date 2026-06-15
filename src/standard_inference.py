import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path
from ultralytics import YOLO

# SAM imports
from segment_anything import sam_model_registry, SamPredictor
from physics_preprocess import preprocess_tem_image

def run_standard_inference(image_path: str, output_path: str):
    print("Loading SOTA Models (Standard Inference for small images)...")
    
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    
    # 1. Load Custom YOLO Model
    # We explicitly load the Phase 1 model (-2) which achieved the optimal balance 
    # of recall and confidence before the semi-supervised confidence collapse.
    weights_path = str(base_dir / "IISc_TEM_Research" / "yolo_baseline_v1-2" / "weights" / "best.pt")
    print(f"Loading optimal Phase 1 weights from: {weights_path}")
        
    yolo_model = YOLO(weights_path)
    
    device_str = "cuda:0" if torch.cuda.is_available() else "cpu"
    
    # 2. Load SAM
    sam_path = str(base_dir / "weights" / "sam_vit_h_4b8939.pth")
    sam = sam_model_registry["vit_h"](checkpoint=sam_path)
    sam.to(device=device_str)
    sam_predictor = SamPredictor(sam)

    # 3. Physics Pre-Processing (SVD + CLAHE)
    print("Applying Physics Pre-Processing...")
    enhanced_image = preprocess_tem_image(image_path)
    image_rgb = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2RGB)
    
    # 4. Standard YOLO Inference (No slicing)
    print("Running Standard YOLO Inference...")
    results = yolo_model.predict(image_rgb, conf=0.15, verbose=False)
    
    boxes = []
    if len(results) > 0 and len(results[0].boxes) > 0:
        boxes_tensor = results[0].boxes.xyxy
        boxes = boxes_tensor.cpu().numpy().tolist()
        
    print(f"YOLO found {len(boxes)} nanoscale loops.")

    # 5. SAM Refinement
    print("Running SAM Refinement...")
    sam_predictor.set_image(image_rgb)
    all_masks = []

    for box in boxes:
        box_np = np.array(box)
        masks, _, _ = sam_predictor.predict(box=box_np, multimask_output=False)
        all_masks.append(masks[0])

    # 6. Visualization
    plt.figure(figsize=(16, 16))
    plt.imshow(image_rgb)

    for mask in all_masks:
        color = np.array([50/255, 255/255, 50/255, 0.5]) # Transparent Green
        h, w = mask.shape[-2:]
        mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
        plt.gca().imshow(mask_image)
        plt.gca().contour(mask, levels=[0.5], colors=['lime'], linewidths=[1.5])

    for box in boxes:
        x_min, y_min, x_max, y_max = box
        rect = plt.Rectangle(
            (x_min, y_min), x_max - x_min, y_max - y_min,
            linewidth=1, edgecolor='yellow', facecolor='none'
        )
        plt.gca().add_patch(rect)

    plt.title(f"SOTA Standard + SAM: {len(boxes)} Defect Loops Quantified", fontsize=18)
    plt.axis('off')
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=600, bbox_inches='tight')
    print(f"Saved publication-ready output to {output_path}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    test_img = str(base_dir / "data" / "input" / "tem13.jpg")
    out_img = str(base_dir / "data" / "output" / "sota_standard_proof.png")
    
    if os.path.exists(test_img):
        run_standard_inference(test_img, out_img)
    else:
        print(f"Test image not found at {test_img}")
