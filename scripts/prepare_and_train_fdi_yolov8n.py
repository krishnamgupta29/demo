import json
import os
import random
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path
import numpy as np
import torch
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def prepare_and_train():
    print("=" * 80)
    print("TASK A: TRAIN YOLOV8N 32-CLASS TOOTH NUMBERING DETECTOR (DENTEX 80/20 SPLIT)")
    print("=" * 80)
    
    json_path = PROJECT_ROOT / "datasets" / "dentex" / "raw" / "training" / "training_data" / "quadrant_enumeration" / "train_quadrant_enumeration.json"
    with open(json_path, "r", encoding="utf-8") as f:
        coco = json.load(f)
        
    xrays_dir = PROJECT_ROOT / "datasets" / "dentex" / "raw" / "training" / "training_data" / "quadrant_enumeration" / "xrays"
    
    # 32 class names in FDI notation
    fdi_classes = []
    class_id_to_fdi = {}
    for q in range(1, 5):
        for p in range(1, 9):
            fdi_num = q * 10 + p
            cls_idx = (q - 1) * 8 + (p - 1)
            fdi_classes.append(f"FDI_{fdi_num}")
            class_id_to_fdi[cls_idx] = fdi_num
            
    print(f"Total images in dataset: {len(coco['images'])}")
    print(f"Total annotations in dataset: {len(coco['annotations'])}")
    
    # Map image annotations
    anns_by_img = defaultdict(list)
    for a in coco["annotations"]:
        anns_by_img[a["image_id"]].append(a)
        
    # Fixed 80/20 split with seed 42
    images = sorted(coco["images"], key=lambda x: x["id"])
    rng = random.Random(42)
    rng.shuffle(images)
    
    n_train = int(len(images) * 0.80)
    train_images = images[:n_train]
    val_images = images[n_train:]
    print(f"Train images: {len(train_images)} (80%)")
    print(f"Val images:   {len(val_images)} (20%)")
    
    # Setup dataset directory
    ds_dir = PROJECT_ROOT / "ml" / "datasets" / "dentex_fdi"
    ds_dir.mkdir(parents=True, exist_ok=True)
    
    for split in ["train", "val"]:
        (ds_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (ds_dir / "labels" / split).mkdir(parents=True, exist_ok=True)
        
    def write_split(img_list, split_name):
        for im in img_list:
            fn = im["file_name"]
            src_img = xrays_dir / fn
            dst_img = ds_dir / "images" / split_name / fn
            
            # Copy or hardlink image
            if not dst_img.exists():
                shutil.copy2(src_img, dst_img)
                
            w = float(im["width"])
            h = float(im["height"])
            
            label_fn = Path(fn).stem + ".txt"
            label_p = ds_dir / "labels" / split_name / label_fn
            
            lines = []
            for a in anns_by_img[im["id"]]:
                q = a["category_id_1"]  # 0..3
                p = a["category_id_2"]  # 0..7
                cls_id = q * 8 + p
                
                # YOLO format: cls x_center y_center width height (normalized)
                bx, by, bw, bh = a["bbox"]
                cx = (bx + bw / 2.0) / w
                cy = (by + bh / 2.0) / h
                nw = bw / w
                nh = bh / h
                
                # Clamp
                cx = max(0.0, min(1.0, cx))
                cy = max(0.0, min(1.0, cy))
                nw = max(0.0, min(1.0, nw))
                nh = max(0.0, min(1.0, nh))
                
                lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
                
            label_p.write_text("\n".join(lines), encoding="utf-8")

    print("Writing YOLO labels...")
    write_split(train_images, "train")
    write_split(val_images, "val")
    
    # Write yaml
    data_yaml = {
        "path": str(ds_dir.resolve()).replace("\\", "/"),
        "train": "images/train",
        "val": "images/val",
        "names": {i: name for i, name in enumerate(fdi_classes)},
        "nc": 32,
        "description": "DENTEX 32-tooth FDI numbering dataset"
    }
    
    yaml_path = ds_dir / "data.yaml"
    import yaml
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_yaml, f, sort_keys=False)
        
    print(f"Created dataset configuration: {yaml_path}")
    
    # Train YOLOv8n
    from ultralytics import YOLO
    
    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Starting training on device: {device} (RTX 2050)...")
    
    model = YOLO("yolov8n.pt")
    
    t_train_start = time.perf_counter()
    train_results = model.train(
        data=str(yaml_path),
        epochs=15,
        batch=8,
        imgsz=640,
        device=device,
        seed=42,
        optimizer="AdamW",
        lr0=0.001,
        cos_lr=True,
        patience=5,
        save=True,
        project=str(PROJECT_ROOT / "runs" / "fdi_train"),
        name="dentex_fdi_yolov8n",
        exist_ok=True,
        verbose=True
    )
    t_train_end = time.perf_counter()
    train_duration_s = t_train_end - t_train_start
    print(f"Training completed in {train_duration_s:.1f} seconds ({train_duration_s/60.0:.2f} minutes).")
    
    best_pt = Path(model.trainer.best)
    print(f"Best checkpoint: {best_pt}")
    
    # Evaluate best checkpoint on held-out validation set
    val_model = YOLO(str(best_pt))
    metrics = val_model.val(data=str(yaml_path), split="val", imgsz=640, device=device)
    
    print("\n" + "=" * 80)
    print("YOLOV8N 32-CLASS FDI DETECTION RESULTS ON HELD-OUT VAL SPLIT (127 IMAGES):")
    print("=" * 80)
    print(f"Box Precision:  {metrics.box.mp:.4f}")
    print(f"Box Recall:     {metrics.box.mr:.4f}")
    print(f"Box mAP50:      {metrics.box.map50:.4f}")
    print(f"Box mAP50-95:   {metrics.box.map:.4f}")
    
    # Export to ONNX
    onnx_target = PROJECT_ROOT / "ml" / "models" / "checkpoints" / "dentex_fdi_yolov8n_best.onnx"
    onnx_target.parent.mkdir(parents=True, exist_ok=True)
    
    exported_path = val_model.export(
        format="onnx",
        opset=12,
        simplify=True,
        dynamic=False,
        imgsz=640
    )
    
    if Path(exported_path) != onnx_target:
        shutil.copy2(exported_path, onnx_target)
        
    print(f"Exported ONNX model to: {onnx_target}")
    
    # Save training metrics summary
    summary = {
        "train_images": len(train_images),
        "val_images": len(val_images),
        "epochs": 15,
        "batch": 8,
        "seed": 42,
        "training_time_s": round(train_duration_s, 2),
        "val_box_precision": round(float(metrics.box.mp), 4),
        "val_box_recall": round(float(metrics.box.mr), 4),
        "val_box_map50": round(float(metrics.box.map50), 4),
        "val_box_map50_95": round(float(metrics.box.map), 4),
        "onnx_model_path": str(onnx_target),
        "onnx_size_bytes": onnx_target.stat().st_size
    }
    
    out_summary = PROJECT_ROOT / "scratch" / "task_a_yolov8n_fdi_train_results.json"
    with open(out_summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote summary to: {out_summary}")

if __name__ == "__main__":
    prepare_and_train()
