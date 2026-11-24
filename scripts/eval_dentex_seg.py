"""Evaluate DENTEX 4-Class YOLOv8n-Seg on the validation split."""
from pathlib import Path
from ultralytics import YOLO
import torch

def main():
    pt_path = Path("models/checkpoints/dentex_yolov8n_seg.pt")
    yaml_path = Path("datasets/dentex/yolo_seg/data.yaml")
    
    print(f"Loading checkpoint: {pt_path}")
    model = YOLO(str(pt_path))
    
    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Running validation on device {device}...")
    
    metrics = model.val(
        data=str(yaml_path),
        split="val",
        device=device,
        batch=4,
        imgsz=640,
        verbose=True
    )
    
    print("\n=== Validation Results ===")
    print("Box Precision:", metrics.box.mp)
    print("Box Recall:", metrics.box.mr)
    print("Box mAP50:", metrics.box.map50)
    print("Box mAP50-95:", metrics.box.map)
    print("\nMask Precision:", metrics.seg.mp)
    print("Mask Recall:", metrics.seg.mr)
    print("Mask mAP50:", metrics.seg.map50)
    print("Mask mAP50-95:", metrics.seg.map)
    
    print("\nClass-wise Box mAP50:", metrics.box.maps)
    print("Class-wise Mask mAP50:", metrics.seg.maps)

if __name__ == "__main__":
    main()
