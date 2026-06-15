import torch
import cv2
import numpy as np
from diffusers import DDPMPipeline, DDPMScheduler
from ddpm_model import TEMDiffusionModel
from pathlib import Path

def generate_samples(num_samples=16, output_dir="synthetic_outputs"):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Generating on device: {device}")
    
    out_path = Path(output_dir)
    out_path.mkdir(exist_ok=True)
    
    # Load the highly trained weights!
    model_path = Path("src/diffusion/weights/diffusion_model.pth")
    model = TEMDiffusionModel(image_size=64).to(device)
    
    if model_path.exists():
        print(f"Loading highly trained weights from {model_path}...")
        # Since the saved weights might be nested under 'model_state_dict' (depending on training script structure) or just a plain state_dict
        checkpoint = torch.load(model_path, map_location=device, weights_only=True)
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)
    else:
        print(f"WARNING: No trained weights found at {model_path}! Using random initialization.")
        
    model.eval()
    
    scheduler = DDPMScheduler(num_train_timesteps=1000)
    
    # Create the pipeline
    pipeline = DDPMPipeline(unet=model.model, scheduler=scheduler)
    pipeline.to(device)
    
    print(f"Generating {num_samples} synthetic TEM loops...")
    
    # Generate images
    images = pipeline(
        batch_size=num_samples, 
        generator=torch.manual_seed(42),
        output_type="np.array"
    ).images
    
    # Save the synthetic images
    for i, img in enumerate(images):
        # Diffusers outputs numpy arrays in [0, 1]. Convert to uint8.
        img_uint8 = (img * 255).astype(np.uint8)
        
        # If the image is (H, W, 1), reshape to (H, W) for cv2
        if len(img_uint8.shape) == 3 and img_uint8.shape[-1] == 1:
            img_uint8 = img_uint8.squeeze(-1)
            
        cv2.imwrite(str(out_path / f"synthetic_loop_{i:03d}.png"), img_uint8)
        
    print(f"Successfully saved {num_samples} hallucinated loops to {output_dir}/")

if __name__ == "__main__":
    generate_samples()
