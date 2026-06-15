import cv2
import numpy as np

def apply_clahe(image: np.ndarray, clip_limit=2.0, tile_grid_size=(8,8)) -> np.ndarray:
    """
    Applies Contrast Limited Adaptive Histogram Equalization (CLAHE)
    to enhance the high-frequency edges of dislocation loops.
    """
    # Convert to grayscale if not already
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
        
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    enhanced = clahe.apply(gray)
    
    # If original was BGR, we convert back to BGR so it plays nicely with other scripts
    if len(image.shape) == 3:
        enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        return enhanced_bgr
    return enhanced

def apply_svd_background_subtraction(image: np.ndarray, keep_singular_values=5) -> np.ndarray:
    """
    Uses Singular Value Decomposition (SVD) to isolate and subtract the 
    smoothly varying background illumination (thickness fringes, bend contours).
    """
    is_bgr = len(image.shape) == 3
    if is_bgr:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
        
    # Perform SVD
    U, S, Vt = np.linalg.svd(gray.astype(np.float32), full_matrices=False)
    
    # The first few singular values represent the low-frequency background
    # We reconstruct the background using ONLY the first `keep_singular_values`
    S_background = np.zeros_like(S)
    S_background[:keep_singular_values] = S[:keep_singular_values]
    
    background = np.dot(U, np.dot(np.diag(S_background), Vt))
    
    # Subtract background from original
    # We add 128 to shift the zero-mean result back to visible spectrum
    foreground = gray.astype(np.float32) - background + 128
    foreground = np.clip(foreground, 0, 255).astype(np.uint8)
    
    if is_bgr:
        return cv2.cvtColor(foreground, cv2.COLOR_GRAY2BGR)
    return foreground

def preprocess_tem_image(image_path: str, output_path: str = None) -> np.ndarray:
    """
    Master function to run SVD -> CLAHE on a given TEM image.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not load image at {image_path}")
        
    # 1. SVD Background Subtraction
    svd_img = apply_svd_background_subtraction(image)
    
    # 2. CLAHE Enhancement
    final_img = apply_clahe(svd_img)
    
    if output_path:
        cv2.imwrite(output_path, final_img)
        
    return final_img

if __name__ == "__main__":
    # Test on a single image if executed directly
    from pathlib import Path
    base_dir = Path(__file__).parent.parent
    test_img = base_dir / "data" / "input" / "tem13.jpg"
    test_out = base_dir / "data" / "output" / "tem13_physics_preprocessed.jpg"
    
    if test_img.exists():
        print(f"Testing physics pre-processor on {test_img}...")
        preprocess_tem_image(str(test_img), str(test_out))
        print(f"Saved enhanced output to {test_out}")
    else:
        print("Test image not found, skipping standalone test.")
