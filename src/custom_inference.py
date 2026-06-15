import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path
from ultralytics import YOLO
from segment_anything import sam_model_registry, SamPredictor

# ==========================================
# 1. LOAD YOUR CUSTOM FINE-TUNED MODEL
# ==========================================
print("Loading Custom Models...")

script_dir = Path(__file__).parent.resolve()
base_dir = script_dir.parent

# Resolve path to the best weights (from our training)
weights_path = str(base_dir / "IISc_TEM_Research" / "yolo_baseline_v1" / "weights" / "best.pt")
if not os.path.exists(weights_path):
    print(f"Warning: Custom weights not found at {weights_path}. Falling back to default.")
    weights_path = "yolo11n.pt"
    
yolo_model = YOLO(weights_path) 

# Load SAM
sam_path = str(base_dir / "weights" / "sam_vit_h_4b8939.pth")
sam = sam_model_registry["vit_h"](checkpoint=sam_path)
sam.to(device="cuda" if torch.cuda.is_available() else "cpu")
sam_predictor = SamPredictor(sam)

# ==========================================
# 2. RUN INFERENCE ON A NEW TEM IMAGE
# ==========================================
image_path = str(base_dir / "data" / "input" / "tem13.jpg") # Pick an image the model HAS NOT seen yet
image = cv2.imread(image_path)
if image is None:
    raise FileNotFoundError(f"Image not found at {image_path}")
image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

print("Running Custom YOLO Detection...")
# We can use a higher confidence now because the model actually knows what a loop is
yolo_results = yolo_model.predict(image_rgb, conf=0.40) 
boxes = yolo_results[0].boxes.xyxy.cpu().numpy()
print(f"Custom YOLO found {len(boxes)} loops.")

# ==========================================
# 3. SAM REFINEMENT
# ==========================================
print("Running SAM Refinement...")
sam_predictor.set_image(image_rgb)
all_masks = []

for box in boxes:
    masks, _, _ = sam_predictor.predict(box=box, multimask_output=False)
    all_masks.append(masks[0])

# ==========================================
# 4. VISUALIZATION
# ==========================================
plt.figure(figsize=(12, 12))
plt.imshow(image_rgb)

for mask in all_masks:
    color = np.array([50/255, 255/255, 50/255, 0.5]) # Transparent Green
    h, w = mask.shape[-2:]
    mask_image = mask.     reshape(h, w, 1) * color.reshape(1, 1, -1)
    plt.gca().imshow(mask_image)
    # Adding contour line to make the boundaries pop!
    plt.gca().contour(mask, levels=[0.5], colors=['lime'], linewidths=[2])

# Draw YOLO bounding boxes for completeness
for box in boxes:
    x_min, y_min, x_max, y_max = box
    rect = plt.Rectangle(
        (x_min, y_min), x_max - x_min, y_max - y_min,
        linewidth=2, edgecolor='yellow', facecolor='none'
    )
    plt.gca().add_patch(rect)

plt.title(f"Fine-Tuned YOLO + SAM: {len(boxes)} Defects Quantified", fontsize=16)
plt.axis('off')
output_path = str(base_dir / "data" / "output" / "final_architecture_proof.png")
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Saved jaw-dropping output to {output_path}")
