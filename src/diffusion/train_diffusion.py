import os
import torch
from torch.utils.data import DataLoader
from torchvision import transforms, datasets
from diffusers import DDPMScheduler
import torch.nn.functional as F
from ddpm_model import TEMDiffusionModel

def train_loop():
    dataset_dir = r"C:\Users\Parardha\Desktop\IIsc Intern\dataset\train"
    image_size = 64
    batch_size = 16
    num_epochs = 500
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device}")
    
    # Simple data augmentation and normalization to [-1, 1]
    transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.Grayscale(num_output_channels=1),
        transforms.ToTensor(),
        transforms.Normalize([0.5], [0.5])
    ])
    
    # Filter out empty directories
    import shutil
    for folder in os.listdir(dataset_dir):
        path = os.path.join(dataset_dir, folder)
        if os.path.isdir(path) and len(os.listdir(path)) == 0:
            os.rmdir(path)
            
    dataset = datasets.ImageFolder(dataset_dir, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    
    model = TEMDiffusionModel(image_size=image_size).to(device)
    
    weights_path = r"C:\Users\Parardha\Desktop\IIsc Intern\src\diffusion\weights\diffusion_model.pth"
    start_epoch = 0
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

    if os.path.exists(weights_path):
        print("Found existing weights! Resuming training from previous session...")
        checkpoint = torch.load(weights_path, map_location=device)
        
        # Check if it's the old format (just weights) or the new format (dict with epoch)
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
            optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            start_epoch = checkpoint['epoch'] + 1
            print(f"Resumed from Epoch {start_epoch}")
        else:
            model.load_state_dict(checkpoint)
            print("Loaded old weight format. Starting counter from Epoch 1 (but AI is fully trained up to the pause point!)")
    else:
        print("No existing weights found. Starting fresh training...")
    
    # Setup DDPM Noise Scheduler
    noise_scheduler = DDPMScheduler(num_train_timesteps=1000)
    
    model.train()
    current_epoch = start_epoch
    try:
        for epoch in range(start_epoch, num_epochs):
            current_epoch = epoch
            for step, (batch_images, _) in enumerate(dataloader):
                batch_images = batch_images.to(device)
                
                # Sample noise to add to the images
                noise = torch.randn_like(batch_images)
                bs = batch_images.shape[0]
                
                # Sample a random timestep for each image
                timesteps = torch.randint(0, noise_scheduler.config.num_train_timesteps, (bs,), device=device).long()
                
                # Add noise to the clean images according to the noise magnitude at each timestep
                noisy_images = noise_scheduler.add_noise(batch_images, noise, timesteps)
                
                # Predict the noise residual
                noise_pred = model(noisy_images, timesteps)
                
                # Compute loss
                loss = F.mse_loss(noise_pred, noise)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                if step % 10 == 0:
                    print(f"Epoch {epoch+1} | Step {step:03d} | Loss: {loss.item():.4f}")
                    
            print(f"Finished Epoch {epoch+1}")
            
            # AUTO-SAVE every 10 epochs to prevent data loss on forceful shutdown
            if (epoch + 1) % 10 == 0:
                print(f"--> [AUTO-SAVE] Checkpointing model at Epoch {epoch+1}...")
                os.makedirs(r"C:\Users\Parardha\Desktop\IIsc Intern\src\diffusion\weights", exist_ok=True)
                
                state_dict = {
                    'epoch': current_epoch,
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                }
                
                # Overwrite the main file to resume easily
                torch.save(state_dict, r"C:\Users\Parardha\Desktop\IIsc Intern\src\diffusion\weights\diffusion_model.pth")
                
                # Create a permanent milestone backup every 50 epochs
                if (epoch + 1) % 50 == 0:
                    backup_path = rf"C:\Users\Parardha\Desktop\IIsc Intern\src\diffusion\weights\diffusion_model_ep{epoch+1}.pth"
                    torch.save(state_dict, backup_path)
                    print(f"--> [MILESTONE BACKUP] Saved permanent backup to {backup_path}")
            
    except KeyboardInterrupt:
        print("\n[WARNING] Training interrupted by user!")
        
    print("\nSaving the Generative AI Model Weights...")
    os.makedirs(r"C:\Users\Parardha\Desktop\IIsc Intern\src\diffusion\weights", exist_ok=True)
    
    torch.save({
        'epoch': current_epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
    }, r"C:\Users\Parardha\Desktop\IIsc Intern\src\diffusion\weights\diffusion_model.pth")
    
    print("Model and Epoch saved successfully! You can resume or generate images now.")

if __name__ == "__main__":
    train_loop()
