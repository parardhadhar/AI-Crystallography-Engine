import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path
from ultralytics import YOLO

def draw_comparison():
    print("Generating Journal-Grade Bounding Box Comparison Slide...")
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    
    # CHANGE THIS TO YOUR SPECIFIC IMAGE
    image_name = "tem13.jpg"
    image_path = str(base_dir / "data" / "input" / image_name)
    
    # The Ground Truth from Label Studio
    ground_truth_txt_path = str(base_dir / "data" / "label_studio_export" / "labels" / f"{os.path.splitext(image_name)[0]}.txt")
    
    output_path = str(base_dir / "data" / "output" / f"comparison_{image_name}")
    
    if not os.path.exists(image_path) or not os.path.exists(ground_truth_txt_path):
        print("ERROR: Could not find image or ground truth label file.")
        print("Please ensure you have exported the Label Studio file.")
        return

    # 1. Load Image
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h_img, w_img, _ = image.shape

    # 2. Read Ground Truth Boxes (Yellow)
    gt_boxes = []
    with open(ground_truth_txt_path, 'r') as f:
        for line in f.readlines():
            parts = line.strip().split()
            if len(parts) == 5:
                _, x_c, y_c, w, h = map(float, parts)
                x1 = int((x_c - w/2) * w_img)
                y1 = int((y_c - h/2) * h_img)
                x2 = int((x_c + w/2) * w_img)
                y2 = int((y_c + h/2) * h_img)
                gt_boxes.append([x1, y1, x2, y2])

    # 3. Generate AI Prediction Boxes (Cyan/Blue)
    weights_path = str(base_dir / "IISc_TEM_Research" / "yolo_baseline_v1-2" / "weights" / "best.pt")
    
    # Optional: If you want SAHI for microscopic loops, we can import SAHI here.
    # For now, using standard YOLO for simplicity. You can swap this to SAHI.
    yolo_model = YOLO(weights_path)
    results = yolo_model.predict(image_rgb, conf=0.15, verbose=False)
    
    pred_boxes = []
    if len(results) > 0 and len(results[0].boxes) > 0:
        pred_boxes = results[0].boxes.xyxy.cpu().numpy().tolist()

    # 4. Draw Boxes
    # OpenCV uses BGR natively, but we are drawing on image_rgb
    
    # Draw Ground Truth (Yellow)
    for box in gt_boxes:
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(image_rgb, (x1, y1), (x2, y2), (255, 255, 0), 2) # Yellow
        
    # Draw Predictions (Cyan)
    for box in pred_boxes:
        x1, y1, x2, y2 = map(int, box)
        # Shift cyan box slightly so it doesn't completely overlap perfectly drawn yellow boxes
        cv2.rectangle(image_rgb, (x1-1, y1-1), (x2+1, y2+1), (0, 255, 255), 2) # Cyan

    # 5. Save and Display
    plt.figure(figsize=(14, 14))
    plt.imshow(image_rgb)
    plt.title("Yellow = Human Ground Truth | Cyan = AI Prediction", fontsize=18)
    plt.axis('off')
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=600, bbox_inches='tight')
    print(f"Saved Journal Comparison Figure to: {output_path}")

if __name__ == "__main__":
    draw_comparison()
