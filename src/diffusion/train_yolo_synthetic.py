from ultralytics import YOLO
import torch
import os
from pathlib import Path

def train_synthetic_yolo():
    device = "0" if torch.cuda.is_available() else "cpu"
    print(f"Training on device: {'GPU' if device == '0' else 'CPU'}")

    script_dir = Path(__file__).parent.resolve()
    
    # Path to our synthetic dataset YAML
    yaml_path = str(script_dir / 'dataset.yaml')
    project_dir = str(script_dir / 'YOLO_Synthetic_Models')

    model = YOLO('yolo11n.pt')

    print("Starting fine-tuning process on GenAI Synthetic Data...")
    results = model.train(
        data=yaml_path,               
        epochs=10,                    # Small number for quick proof of concept
        imgsz=512,                    
        batch=4,                      
        device=device,
        optimizer='AdamW',            
        lr0=0.001,                    
        project=project_dir,          
        name='yolo_synthetic_v1'       
    )
    
    print(f"Training complete! Best weights saved to {project_dir}/yolo_synthetic_v1/weights/best.pt")

if __name__ == '__main__':
    train_synthetic_yolo()
