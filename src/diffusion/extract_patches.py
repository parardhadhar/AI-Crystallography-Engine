import os
import cv2
import pandas as pd
import numpy as np
from pathlib import Path

def extract_dataset(csv_path, img_dir, out_dir, patch_size=64):
    print(f"Extracting synthetic dataset from {csv_path}")
    df = pd.read_csv(csv_path)
    
    out_path = Path(out_dir)
    classes = ["Perfect", "Faulted", "Edge-on", "Unknown"]
    for c in classes:
        (out_path / c).mkdir(parents=True, exist_ok=True)
        
    # Pre-load images to avoid opening them thousands of times
    images = {}
    
    count = 0
    for idx, row in df.iterrows():
        img_name = row["Image"]
        if pd.isna(img_name): continue
        
        if img_name not in images:
            full_img_path = os.path.join(img_dir, img_name)
            if not os.path.exists(full_img_path):
                print(f"Warning: Missing image {full_img_path}")
                continue
            images[img_name] = cv2.imread(full_img_path, cv2.IMREAD_GRAYSCALE)
            if images[img_name] is None:
                print(f"Failed to load {full_img_path}")
                continue
                
        img = images[img_name]
        h, w = img.shape
        
        x = int(float(row["X_Coord"]))
        y = int(float(row["Y_Coord"]))
        
        # Determine class based on the rigorous math classification!
        c_str = str(row["Classified_Burgers_Vector"])
        ratio_str = "1.0"
        if "Ratio: " in c_str:
            try:
                ratio_str = c_str.split("Ratio: ")[1].split(")")[0]
            except: pass
            
        cls = "Unknown"
        try: ratio = float(ratio_str)
        except: ratio = 1.0
        
        if ratio < 0.25:
            cls = "Edge-on"
        elif "1/2<110>" in c_str and "1/3<111>" not in c_str:
            cls = "Perfect"
        elif "1/3<111>" in c_str and "1/2<110>" not in c_str:
            cls = "Faulted"
        elif "1/2<111>" in c_str:
            cls = "Perfect"
            
        # Crop patch
        half_p = patch_size // 2
        x1, x2 = x - half_p, x + half_p
        y1, y2 = y - half_p, y + half_p
        
        # Bound checks
        if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
            # Skip edge defects
            continue
            
        patch = img[y1:y2, x1:x2]
        
        patch_filename = f"{img_name}_loop_{idx:05d}_{ratio_str}.png"
        save_path = out_path / cls / patch_filename
        
        cv2.imwrite(str(save_path), patch)
        count += 1
        
        if count % 500 == 0:
            print(f"Extracted {count} patches...")
            
    print(f"\nExtraction complete! Total unique physical loop patches: {count}")
    
    for c in classes:
        num = len(list((out_path / c).glob("*.png")))
        print(f" -> {c}: {num}")

if __name__ == "__main__":
    base_dir = r"C:\Users\Parardha\Desktop\IIsc Intern"
    csv = os.path.join(base_dir, "iisc output", "100nm phase 1 training with iisc data", "crystallography_report.csv")
    img_dir = os.path.join(base_dir, "Iisc100nm")
    out_dir = os.path.join(base_dir, "dataset", "train")
    
    extract_dataset(csv, img_dir, out_dir, patch_size=64)
