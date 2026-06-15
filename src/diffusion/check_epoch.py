import torch
import os

path1 = r"C:\Users\Parardha\Desktop\IIsc Intern\src\diffusion\weights\diffusion_model.pth"
path2 = r"C:\Users\Parardha\Desktop\IIsc Intern\src\diffusion\weights\diffusion_model_SAFE_BACKUP_300.pth"

for path in [path1, path2]:
    print(f"\nChecking: {os.path.basename(path)}")
    try:
        data = torch.load(path, map_location='cpu', weights_only=False)
        if isinstance(data, dict) and 'epoch' in data:
            print(f"[SUCCESS] This file uses the new format! Stored Epoch Number: {data['epoch']}")
        elif isinstance(data, dict): 
            # If it's a dict but has no 'epoch', it's likely just the raw state_dict (which is also a dict)
            print(f"[WARNING] OLD FORMAT (Raw Weights Only). The AI weights are 100% here, but the script didn't save the epoch number text.")
        else:
            print(f"Format type: {type(data)}")
    except Exception as e:
        print(f"Error loading: {e}")
