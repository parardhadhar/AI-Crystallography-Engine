import cv2
import numpy as np

def align_images(reference_image_path, target_image_path):
    """
    Mathematically aligns a target g-vector image to a reference multibeam image
    using ORB feature matching and Homography transformations.
    """
    print(f"Aligning {target_image_path} to reference...")
    
    # 1. Load images in grayscale
    img_ref = cv2.imread(reference_image_path, cv2.IMREAD_GRAYSCALE)
    img_target = cv2.imread(target_image_path, cv2.IMREAD_GRAYSCALE)
    
    if img_ref is None or img_target is None:
        raise ValueError("Could not load one or both images for registration.")

    # 2. Detect ORB features and compute descriptors
    # We use 5000 features for extremely precise pixel-level matching
    orb = cv2.ORB_create(5000)
    keypoints_ref, descriptors_ref = orb.detectAndCompute(img_ref, None)
    keypoints_target, descriptors_target = orb.detectAndCompute(img_target, None)

    # 3. Match features using Hamming distance
    matcher = cv2.DescriptorMatcher_create(cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING)
    matches = matcher.match(descriptors_target, descriptors_ref, None)

    # 4. Sort matches by score (keep the best 20%)
    matches.sort(key=lambda x: x.distance, reverse=False)
    num_good_matches = int(len(matches) * 0.2)
    matches = matches[:num_good_matches]

    # 5. Extract location of good matches
    points_ref = np.zeros((len(matches), 2), dtype=np.float32)
    points_target = np.zeros((len(matches), 2), dtype=np.float32)

    for i, match in enumerate(matches):
        points_ref[i, :] = keypoints_ref[match.trainIdx].pt
        points_target[i, :] = keypoints_target[match.queryIdx].pt

    # 6. Find the Homography Matrix (The mathematical transformation)
    # RANSAC ignores outliers (like loops that vanished in the target image!)
    h_matrix, inliers = cv2.findHomography(points_target, points_ref, cv2.RANSAC)

    # 7. Warp the target image to perfectly align with the reference
    height, width = img_ref.shape
    aligned_target = cv2.warpPerspective(img_target, h_matrix, (width, height))
    
    print("Alignment complete.")
    return img_ref, aligned_target, h_matrix

if __name__ == "__main__":
    # Test script if run directly
    print("Image Registration Module loaded. Ready for Differential Analysis.")
