import cv2
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from morphology_detector import MorphologyDetector
from sam_segmenter import SAMSegmenter

image_bgr = cv2.imread(r'C:\Users\Parardha\.gemini\antigravity-ide\brain\1f3c9d96-275c-46f6-8146-0e85a9a14221\final_cryst_23.tif')
image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

scale = 120
scale_nm_per_pixel = 100.0 / scale if scale > 0 else None

MATH_CORE = MorphologyDetector(
    kernel_size=(35, 35),
    max_sigma=15,
    threshold=0.1,
    scale_nm_per_pixel=scale_nm_per_pixel
)

AI_CORE = SAMSegmenter(model_type="vit_h", checkpoint_path="C:/Users/Parardha/Desktop/IIsc Intern/weights/sam_vit_h_4b8939.pth")

print("Running Morph...")
boxes, diameters = MATH_CORE.get_bounding_boxes(image_bgr, return_diameters=True)
print(f"Found {len(boxes)} boxes.")

print("Running SAM...")
sam_masks = AI_CORE.generate_masks(image_rgb, boxes)
print(f"SAM returned {len(sam_masks)} masks.")

print("Looping through masks...")
for idx, contour in enumerate(sam_masks):
    if contour is None: continue
    area_pixels = float(cv2.contourArea(contour))
    if area_pixels < 16: continue
    
    rect = cv2.minAreaRect(contour)
    w_rect, h_rect = rect[1]
    
    print(f"Mask {idx}: perimeter...")
    perimeter = cv2.arcLength(contour, True)
    
    if len(contour) >= 5:
        print(f"Mask {idx}: fitEllipse...")
        (xc, yc), (d1, d2), _ = cv2.fitEllipse(contour)
        
    print(f"Mask {idx}: drawContours...")
    h, w = image_rgb.shape[:2]
    mask_2d = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(mask_2d, [contour], -1, 255, cv2.FILLED)

print("Done successfully!")
