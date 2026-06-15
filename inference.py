import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
from ultralytics import YOLO
from segment_anything import sam_model_registry, SamPredictor

# ==========================================
# 1. INITIALIZE MODELS
# ==========================================
print("Loading Models...")
# Load YOLO (Use standard YOLO11n if you haven't trained your own yet)
yolo_model = YOLO("yolo11n.pt") 

# Load SAM (Segment Anything)
sam_checkpoint = "sam_vit_h_4b8939.pth" # Make sure this file is in your folder
model_type = "vit_h"
device = "cuda" if torch.cuda.is_available() else "cpu"

sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
sam.to(device=device)
sam_predictor = SamPredictor(sam)

# ==========================================
# 2. LOAD AND PROCESS THE TEM IMAGE
# ==========================================
image_path = "Tem Images/tem13.jpg" # Replace with your downloaded TEM image
image = cv2.imread(image_path)
image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# ==========================================
# 3. STEP 1: YOLO DETECTION (Find the loops)
# ==========================================
print("Running YOLO Detection...")
# Lower confidence for now since it's an untrained model on TEM data
yolo_results = yolo_model.predict(image_rgb, conf=0.15) 

# Extract bounding boxes in [x_min, y_min, x_max, y_max] format
boxes = yolo_results[0].boxes.xyxy.cpu().numpy()
print(f"Found {len(boxes)} potential defects.")

# ==========================================
# 4. STEP 2: SAM REFINEMENT (Pixel-perfect masks)
# ==========================================
print("Running SAM Refinement...")
sam_predictor.set_image(image_rgb)
all_masks = []

# Feed every YOLO box into SAM to generate a tight mask
for box in boxes:
    # SAM takes the box coordinates as a prompt
    masks, scores, logits = sam_predictor.predict(
        box=box,
        multimask_output=False # We want the single best mask per loop
    )
    all_masks.append(masks[0]) # Save the mask

# ==========================================
# 5. VISUALIZATION (To show the Professor)
# ==========================================
plt.figure(figsize=(10, 10))
plt.imshow(image_rgb)

# Draw SAM Masks (in green with transparency)
for mask in all_masks:
    color = np.array([30/255, 255/255, 30/255, 0.5]) # Transparent Green
    h, w = mask.shape[-2:]
    mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
    plt.gca().imshow(mask_image)

# Draw YOLO Bounding Boxes (in red)
for box in boxes:
    x0, y0, x1, y1 = box
    plt.gca().add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, 
                                      edgecolor='red', facecolor='none', lw=2))

plt.title("YOLO Detection (Red) + SAM Segmentation (Green)")
plt.axis('off')
plt.show()
