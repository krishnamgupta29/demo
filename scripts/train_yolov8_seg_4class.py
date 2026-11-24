"""
Training and Fine-Tuning Pipeline for DENTEX 4-Class YOLOv8-Seg.

Compulsory Targets:
0: impacted_tooth
1: caries
2: periapical_lesion
3: deep_caries

Hardware-aware configuration:
- Batch size = 8 (constrained by RTX 2050 4 GB VRAM)
- Mixed precision FP16 (AMP)
- Early stopping patience = 10
- Deterministic seed = 42
- Automatically exports fine-tuned checkpoint to ONNX format (opset 17)
"""

import argparse
import os
from pathlib import Path
import sys
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_training(
    model_variant: str = "yolov8n-seg.pt",
    epochs: int = 30,
    batch_size: int = 8,
    img_size: int = 640,
    device: str = "auto",
):
    print("=== DENTRACE Level 3: 4-Class YOLOv8-Seg Training Pipeline ===")

    try:
        from ultralytics import YOLO
        import torch
    except ImportError:
        print("ERROR: ultralytics and torch are required to run training.")
        sys.exit(1)

    # Resolve device
    if device == "auto":
        if torch.cuda.is_available():
            dev = 0
            dev_name = torch.cuda.get_device_name(0)
            print(f"CUDA detected: Using GPU {dev_name} with AMP mixed precision.")
        else:
            dev = "cpu"
            print("CUDA not detected: Using CPU.")
    else:
        dev = device

    data_yaml = PROJECT_ROOT / "datasets" / "dentex" / "yolo_seg" / "data.yaml"
    if not data_yaml.exists():
        print(f"ERROR: Dataset YAML missing at {data_yaml}. Run scripts/prepare_yolo_seg_dataset.py first.")
        sys.exit(1)

    output_project = Path("C:/mini/models/experiments")
    run_name = "dentex_yolov8n_seg_4class_v2"

    # Use local pretrained checkpoint if available
    local_pretrained = PROJECT_ROOT / "models" / "checkpoints" / "pretrained" / "yolov8n-seg.pt"
    if local_pretrained.exists():
        model_variant = str(local_pretrained)

    print(f"Loading base architecture: {model_variant}")
    model = YOLO(model_variant)

    print(f"Starting training on {data_yaml} for {epochs} epochs (batch={batch_size}, imgsz={img_size})...")

    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        batch=batch_size,
        imgsz=img_size,
        device=dev,
        project=str(output_project),
        name=run_name,
        seed=42,
        deterministic=True,
        patience=10,
        save=True,
        workers=2,
        half=torch.cuda.is_available(),
        exist_ok=True,
        verbose=True,
    )

    print("\n=== Training Completed ===")
    best_pt = output_project / run_name / "weights" / "best.pt"
    if best_pt.exists():
        target_pt = PROJECT_ROOT / "models" / "checkpoints" / "dentex_yolov8n_seg.pt"
        import shutil
        shutil.copy(best_pt, target_pt)
        print(f"Best checkpoint saved and deployed to: {target_pt}")
        print("Exporting best checkpoint to ONNX format (opset 17)...")
        best_model = YOLO(str(target_pt))
        exported_onnx = best_model.export(format="onnx", imgsz=img_size, opset=17)
        target_onnx = PROJECT_ROOT / "models" / "checkpoints" / "dentex_yolov8n_seg.onnx"
        if Path(exported_onnx).resolve() != target_onnx.resolve():
            shutil.copy(exported_onnx, target_onnx)
        print(f"ONNX export successful: {target_onnx}")
    else:
        print(f"Warning: Checkpoint not found at {best_pt}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train DENTEX 4-Class YOLOv8-Seg")
    parser.add_argument("--model", type=str, default="yolov8n-seg.pt", help="Base model (yolov8n-seg.pt or yolov8s-seg.pt)")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=8, help="Batch size (default: 8 for RTX 2050 4GB)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--device", type=str, default="auto", help="Device (0, cpu, or auto)")

    args = parser.parse_args()
    run_training(
        model_variant=args.model,
        epochs=args.epochs,
        batch_size=args.batch,
        img_size=args.imgsz,
        device=args.device,
    )
