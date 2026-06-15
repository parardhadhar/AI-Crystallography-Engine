from ultralytics import YOLO
import torch
import os
from pathlib import Path

def fine_tune_yolo_tem():
    # 1. Check for GPU (Critical for 30-day timeline)
    device = "0" if torch.cuda.is_available() else "cpu"
    print(f"Training on device: {'GPU' if device == '0' else 'CPU'}")

    # Resolve paths correctly relative to script location
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    weights_path = str(base_dir / 'weights' / 'yolo11n.pt')
    yaml_path = str(base_dir / 'tem_dataset' / 'data.yaml')
    project_dir = str(base_dir / 'IISc_TEM_Research')

    # 2. Load the base YOLO11 Nano model
    # We use 'nano' (n) because it's fast and we will use SAM for the heavy lifting later
    model = YOLO(weights_path if os.path.exists(weights_path) else 'yolo11n.pt')

    # 3. Start Fine-Tuning on TEM Data
    print("Starting fine-tuning process...")
    results = model.train(
        data=yaml_path,               # Path to your dataset config
        epochs=300,                   # 300 for Phase 2 Publication Quality
        imgsz=640,                    # Standard resolution
        batch=16,                     # Adjust to 8 if you run out of GPU memory
        device=device,
        
        # --- SCIENTIFIC IMAGING OPTIMIZATIONS ---
        patience=30,                  # Stop early if no improvement for 30 epochs
        optimizer='AdamW',            # Better for small, complex datasets
        lr0=0.001,                    # Slightly lower learning rate so it doesn't overfit
        
        # Augmentations to handle varying TEM magnifications and angles
        mosaic=0.5,                   # Combines 4 images to teach it dense clusters
        degrees=45.0,                 # Loops can be oriented in any direction
        flipud=0.5,                   # Up-down flips are valid in TEM projections
        fliplr=0.5,                   # Left-right flips are valid
        
        project=project_dir,          # Folder to save your weights
        name='yolo_baseline_v1'       # Experiment name
    )
    
    print(f"Training complete! Best weights saved to {project_dir}/yolo_baseline_v1/weights/best.pt")

if __name__ == '__main__':
    fine_tune_yolo_tem()
