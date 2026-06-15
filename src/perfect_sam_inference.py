import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path
from segment_anything import sam_model_registry, SamPredictor

def generate_perfect_slide():
    # 1. Paths
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    
    # CHANGE THESE TO YOUR SPECIFIC FILES AFTER LABEL STUDIO EXPORT
    # Currently pointing to tem13.jpg as an example
    image_name = "tem13.jpg"
    image_path = str(base_dir / "data" / "input" / image_name)
    yolo_txt_path = str(base_dir / "data" / "label_studio_export" / "labels" / f"{os.path.splitext(image_name)[0]}.txt")
    output_path = str(base_dir / "data" / "output" / "perfect_presentation_slide.png")
    
    if not os.path.exists(image_path) or not os.path.exists(yolo_txt_path):
        print(f"ERROR: Could not find image or label file.")
        print(f"Please ensure {image_path} and {yolo_txt_path} exist.")
        return

    # 2. Load Image
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h_img, w_img, _ = image.shape

    # 3. Read the Perfect Bounding Boxes from Label Studio
    boxes = []
    with open(yolo_txt_path, 'r') as f:
        for line in f.readlines():
            parts = line.strip().split()
            if len(parts) != 5:
                continue
                
            class_id, x_center, y_center, width, height = map(float, parts)
            
            # Convert YOLO format (normalized center) back to SAM format (pixel xyxy)
            x1 = int((x_center - width/2) * w_img)
            y1 = int((y_center - height/2) * h_img)
            x2 = int((x_center + width/2) * w_img)
            y2 = int((y_center + height/2) * h_img)
            boxes.append([x1, y1, x2, y2])

    # 4. Load SAM
    print("Loading SAM...")
    sam_checkpoint = str(base_dir / "weights" / "sam_vit_h_4b8939.pth")
    sam = sam_model_registry["vit_h"](checkpoint=sam_checkpoint)
    sam.to(device="cuda" if torch.cuda.is_available() else "cpu")
    predictor = SamPredictor(sam)
    predictor.set_image(image_rgb)

    # 5. Generate Perfect Masks
    print("Generating masks based on perfect bounding boxes...")
    all_masks = []
    for box in boxes:
        # We pass the EXACT box to SAM
        masks, scores, _ = predictor.predict(box=np.array(box), multimask_output=False)
        all_masks.append(masks[0])

    # 6. Visualization (The Checkmate Slide)
    plt.figure(figsize=(12, 12))
    plt.imshow(image_rgb)

    for mask in all_masks:
        color = np.array([50/255, 255/255, 50/255, 0.6]) # Crisp, transparent green
        h, w = mask.shape[-2:]
        mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
        plt.gca().imshow(mask_image)
        # Optional: Add a crisp border to the mask
        plt.gca().contour(mask, levels=[0.5], colors=['lime'], linewidths=[1.5])

    plt.title(f"Human-in-the-Loop SAM Segmentation: {len(boxes)} Defects Quantified", fontsize=18)
    plt.axis('off')
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=600, bbox_inches='tight')
    print(f"Saved Checkmate Slide to: {output_path}")

if __name__ == "__main__":
    generate_perfect_slide()
