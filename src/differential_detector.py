import cv2
import numpy as np

def generate_morphology_map(img_ref_aligned, img_target_aligned, threshold_value=30):
    """
    Performs Mathematical Image Subtraction to detect loops that vanished 
    in the target g-vector image compared to the reference image.
    """
    print("Generating Differential Morphology Map...")
    
    # 1. Ensure images are float32 to prevent underflow during subtraction
    ref_float = img_ref_aligned.astype(np.float32)
    target_float = img_target_aligned.astype(np.float32)
    
    # 2. Mathematical Subtraction
    # We subtract Target from Reference. 
    # If a dark loop exists in Ref but is missing in Target, 
    # Ref will have low pixel values (dark), Target will have high pixel values (light background).
    # Wait, actually if it's dark in Ref and missing (light) in Target:
    # Target - Ref = Light - Dark = High Positive Value (The Vanished Loop!)
    diff_map = cv2.absdiff(target_float, ref_float)
    
    # Normalize to 0-255 for thresholding
    diff_map = cv2.normalize(diff_map, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    
    # 3. Morphological Thresholding
    # Only keep the highly distinct differences (the vanishing loops)
    _, binary_map = cv2.threshold(diff_map, threshold_value, 255, cv2.THRESH_BINARY)
    
    # 4. Mathematical Morphology (Clean up noise)
    kernel = np.ones((3,3), np.uint8)
    # Opening removes tiny specks of noise
    binary_map = cv2.morphologyEx(binary_map, cv2.MORPH_OPEN, kernel, iterations=1)
    # Dilation merges broken loop fragments
    binary_map = cv2.dilate(binary_map, kernel, iterations=1)
    
    # 5. Extract the Vanished Loops (Contours)
    contours, _ = cv2.findContours(binary_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    vanished_loops = []
    for cnt in contours:
        # Filter out impossibly small or impossibly massive differences
        area = cv2.contourArea(cnt)
        if 50 < area < 10000:
            # We found a mathematically verified loop!
            x, y, w, h = cv2.boundingRect(cnt)
            vanished_loops.append((x, y, w, h))
            
    print(f"Mathematical Subtraction isolated {len(vanished_loops)} vanished loops.")
    return diff_map, binary_map, vanished_loops

if __name__ == "__main__":
    print("Differential Detector Module loaded.")
