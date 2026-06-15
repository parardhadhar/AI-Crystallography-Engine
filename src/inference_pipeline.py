import os
import argparse
from pathlib import Path
from typing import List

import cv2
import numpy as np
import torch
from ultralytics import YOLO
from segment_anything import sam_model_registry, SamPredictor


class DefectSegmentationPipeline:
    """
    Two-stage computer vision inference pipeline for nanoscale irradiation-induced 
    dislocation loops in Transmission Electron Microscopy (TEM) images.
    
    Stage 1: YOLO object detection (Bounding boxes)
    Stage 2: Segment Anything Model (SAM) refinement (Pixel-perfect instance masks)
    """

    def __init__(
        self,
        yolo_weights: str,
        sam_checkpoint: str,
        sam_model_type: str = "vit_h",
        device: str = None
    ):
        """
        Initializes the YOLO and SAM models.

        Args:
            yolo_weights (str): Path to the YOLO model weights.
            sam_checkpoint (str): Path to the SAM checkpoint file.
            sam_model_type (str): Type of the SAM model (default 'vit_h').
            device (str): Device to run the models on ('cuda' or 'cpu'). If None, auto-detected.
        """
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        print(f"Initializing pipeline on device: {self.device}")

        # Initialize YOLO
        print(f"Loading YOLO model from {yolo_weights}...")
        self.yolo_model = YOLO(yolo_weights)

        # Initialize SAM
        print(f"Loading SAM model ({sam_model_type}) from {sam_checkpoint}...")
        sam = sam_model_registry[sam_model_type](checkpoint=sam_checkpoint)
        sam.to(device=self.device)
        self.sam_predictor = SamPredictor(sam)

    def run_yolo(self, image_rgb: np.ndarray, conf_threshold: float = 0.15) -> np.ndarray:
        """
        Runs the YOLO model to detect bounding boxes.

        Args:
            image_rgb (np.ndarray): RGB image array.
            conf_threshold (float): Confidence threshold for YOLO detection.

        Returns:
            np.ndarray: Bounding boxes in format [N, 4] with (x_min, y_min, x_max, y_max).
        """
        results = self.yolo_model.predict(image_rgb, conf=conf_threshold, verbose=False)
        boxes = results[0].boxes.xyxy.cpu().numpy()
        return boxes

    def run_sam(self, image_rgb: np.ndarray, boxes: np.ndarray) -> List[np.ndarray]:
        """
        Runs the SAM model to generate instance masks from bounding box prompts.

        Args:
            image_rgb (np.ndarray): RGB image array.
            boxes (np.ndarray): Bounding boxes [N, 4] from YOLO.

        Returns:
            List[np.ndarray]: List of boolean mask arrays.
        """
        self.sam_predictor.set_image(image_rgb)
        all_masks = []
        
        for box in boxes:
            masks, _, _ = self.sam_predictor.predict(
                box=box,
                multimask_output=False
            )
            all_masks.append(masks[0])
            
        return all_masks

    def generate_three_panel_visualization(
        self,
        image_rgb: np.ndarray,
        boxes: np.ndarray,
        masks: List[np.ndarray],
        output_path: str
    ):
        """
        Generates and saves a 3-panel visualization:
        1. Original Image
        2. YOLO Detection (Yellow bounding boxes)
        3. SAM Refinement (Yellow boxes + Cyan mask boundaries)
        """
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        
        # Set up a dark background style to match the presentation vibe
        plt.style.use('dark_background')
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # --- Panel 1: Original Image ---
        axes[0].imshow(image_rgb)
        axes[0].set_title("Panel 1: Grainy TEM Reality", fontsize=16, pad=10, color='white', fontweight='bold')
        axes[0].axis('off')
        
        # --- Panel 2: YOLO Detection ---
        axes[1].imshow(image_rgb)
        for box in boxes:
            x_min, y_min, x_max, y_max = box
            rect = patches.Rectangle(
                (x_min, y_min), x_max - x_min, y_max - y_min,
                linewidth=3, edgecolor='yellow', facecolor='none'
            )
            axes[1].add_patch(rect)
        axes[1].set_title("Panel 2: YOLO Detection", fontsize=16, pad=10, color='yellow', fontweight='bold')
        axes[1].axis('off')
        
        # --- Panel 3: SAM Refinement ---
        axes[2].imshow(image_rgb)
        for box in boxes:
            x_min, y_min, x_max, y_max = box
            rect = patches.Rectangle(
                (x_min, y_min), x_max - x_min, y_max - y_min,
                linewidth=1, edgecolor='yellow', facecolor='none', alpha=0.5
            )
            axes[2].add_patch(rect)
            
        for mask in masks:
            # Draw mask boundary using contour
            axes[2].contour(mask, levels=[0.5], colors=['cyan'], linewidths=[3])
            
        axes[2].set_title("Panel 3: SAM Refinement", fontsize=16, pad=10, color='cyan', fontweight='bold')
        axes[2].axis('off')
        
        plt.tight_layout()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        # Deep blue background similar to the reference image
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='#0B1B3D')
        plt.close(fig)

    def process_image(self, input_path: str, output_path: str, conf_threshold: float = 0.15):
        """
        End-to-end pipeline processing for a single image.

        Args:
            input_path (str): Path to input image.
            output_path (str): Path to save the output image.
            conf_threshold (float): Confidence threshold for YOLO detection.
        """
        print(f"\nProcessing {input_path}...")
        
        # Load Image
        image_bgr = cv2.imread(input_path)
        if image_bgr is None:
            raise FileNotFoundError(f"Image not found at {input_path}")
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        # Stage 1: YOLO Detection
        boxes = self.run_yolo(image_rgb, conf_threshold=conf_threshold)
        print(f"YOLO Stage: Found {len(boxes)} potential defects.")

        # Stage 2: SAM Refinement
        masks = self.run_sam(image_rgb, boxes)
        print(f"SAM Stage: Generated {len(masks)} instance masks.")

        # Visualization Overlay
        self.generate_three_panel_visualization(image_rgb, boxes, masks, output_path)
        print(f"3-Panel result saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="YOLO-to-SAM Inference Pipeline for TEM images")
    parser.add_argument("--input", type=str, required=True, help="Path to input image")
    parser.add_argument("--output", type=str, required=True, help="Path to save output image")
    parser.add_argument("--yolo_weights", type=str, default="../weights/yolo11n.pt", help="Path to YOLO weights")
    parser.add_argument("--sam_checkpoint", type=str, default="../weights/sam_vit_h_4b8939.pth", help="Path to SAM checkpoint")
    parser.add_argument("--conf", type=float, default=0.15, help="YOLO confidence threshold")
    
    args = parser.parse_args()

    # Determine paths based on script location to handle relative paths gracefully
    script_dir = Path(__file__).parent.resolve()
    
    # Check absolute vs relative paths
    yolo_weights = args.yolo_weights if os.path.isabs(args.yolo_weights) else str(script_dir / args.yolo_weights)
    sam_checkpoint = args.sam_checkpoint if os.path.isabs(args.sam_checkpoint) else str(script_dir / args.sam_checkpoint)

    try:
        pipeline = DefectSegmentationPipeline(
            yolo_weights=yolo_weights,
            sam_checkpoint=sam_checkpoint
        )
        pipeline.process_image(args.input, args.output, conf_threshold=args.conf)
    except Exception as e:
        print(f"Pipeline Execution Failed: {str(e)}")


if __name__ == "__main__":
    main()
