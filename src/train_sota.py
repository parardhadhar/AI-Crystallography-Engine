import os
import torch
from pathlib import Path
from ultralytics import YOLO

def train_sota_model():
    print("Initializing Ultimate SOTA Phase 2 Training...")
    
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    data_yaml_path = base_dir / "tem_dataset" / "data.yaml"
    
    if not data_yaml_path.exists():
        raise FileNotFoundError(f"Cannot find dataset config at {data_yaml_path}")
        
    device = "0" if torch.cuda.is_available() else "cpu"
    if device == "0":
        print("CUDA detected! Training on GPU...")
        
    # We train from the base YOLO11n model to prevent catastrophic forgetting
    # and let it learn purely from the mathematically cleansed dataset.
    model = YOLO("yolo11n.pt") 
    
    print("Starting SOTA training run...")
    results = model.train(
        data=str(data_yaml_path),
        epochs=300, # 300 epochs for maximum convergence on the clean data
        imgsz=640,
        batch=16,
        device=device,
        name="yolo_sota_master", # New pristine project directory
        project=str(base_dir / "IISc_TEM_Research")
    )
    
    print(f"SOTA Training Complete! Weights saved to IISc_TEM_Research/yolo_sota_master")

if __name__ == "__main__":
    train_sota_model()
