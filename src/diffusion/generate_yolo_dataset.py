import os
import cv2
import numpy as np
import random
import torch
from diffusers import DDPMPipeline, DDPMScheduler
from ddpm_model import TEMDiffusionModel
from pathlib import Path

def create_background(size=(512, 512)):
    # Generate a realistic-looking noisy background
    bg = np.random.normal(loc=128, scale=20, size=size).astype(np.float32)
    bg = cv2.GaussianBlur(bg, (5, 5), 0)
    # Add some large scale gradients
    grad_x = np.linspace(-30, 30, size[1])
    grad_y = np.linspace(-30, 30, size[0])
    X, Y = np.meshgrid(grad_x, grad_y)
    bg += X + Y
    bg = np.clip(bg, 0, 255).astype(np.uint8)
    return bg

def generate_yolo_dataset(num_images=20, loops_per_image=(5, 12), output_dir="yolo_dataset"):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Load diffusion model
    model_path = Path("src/diffusion/weights/diffusion_model.pth")
    model = TEMDiffusionModel(image_size=64).to(device)
    if model_path.exists():
        checkpoint = torch.load(model_path, map_location=device, weights_only=True)
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)
    else:
        print("No weights found. Synthetic loops will look like random noise!")
        
    model.eval()
    scheduler = DDPMScheduler(num_train_timesteps=1000)
    pipeline = DDPMPipeline(unet=model.model, scheduler=scheduler)
    pipeline.to(device)
    
    # Setup directories
    img_dir = Path(output_dir) / "images" / "train"
    lbl_dir = Path(output_dir) / "labels" / "train"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {num_images} synthetic TEM images with bounding boxes...")
    
    for i in range(num_images):
        num_loops = random.randint(*loops_per_image)
        bg = create_background((512, 512))
        
        # Generate batch of loops
        images = pipeline(
            batch_size=num_loops, 
            num_inference_steps=20,
            generator=torch.manual_seed(i), # ensure determinism
            output_type="np.array"
        ).images
        
        labels = []
        for j, loop_img in enumerate(images):
            # Format loop
            l_img = (loop_img * 255).astype(np.uint8)
            if len(l_img.shape) == 3 and l_img.shape[-1] == 1:
                l_img = l_img.squeeze(-1)
                
            # Random scale 
            scale = random.uniform(0.6, 1.2)
            new_size = int(64 * scale)
            l_img = cv2.resize(l_img, (new_size, new_size))
            
            # Random rotation
            angle = random.uniform(0, 360)
            M = cv2.getRotationMatrix2D((new_size//2, new_size//2), angle, 1)
            l_img = cv2.warpAffine(l_img, M, (new_size, new_size), borderMode=cv2.BORDER_REPLICATE)
            
            # Random position
            x = random.randint(0, 512 - new_size)
            y = random.randint(0, 512 - new_size)
            
            # Blend
            Y_c, X_c = np.ogrid[:new_size, :new_size]
            dist_from_center = np.sqrt((X_c - new_size/2)**2 + (Y_c - new_size/2)**2)
            mask = np.clip(1 - (dist_from_center / (new_size/2.5)), 0, 1)
            
            bg_roi = bg[y:y+new_size, x:x+new_size]
            bg[y:y+new_size, x:x+new_size] = (l_img * mask + bg_roi * (1 - mask)).astype(np.uint8)
            
            # YOLO format: class x_center y_center width height (normalized)
            x_center = (x + new_size/2) / 512.0
            y_center = (y + new_size/2) / 512.0
            width = (new_size * 0.8) / 512.0 # Slightly tighter bounding box
            height = (new_size * 0.8) / 512.0
            
            labels.append(f"0 {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
            
        cv2.imwrite(str(img_dir / f"syn_{i:04d}.png"), bg)
        with open(lbl_dir / f"syn_{i:04d}.txt", "w") as f:
            f.write("\n".join(labels))
            
        print(f"Image {i+1}/{num_images} generated with {num_loops} loops.")

if __name__ == "__main__":
    generate_yolo_dataset(num_images=20)
