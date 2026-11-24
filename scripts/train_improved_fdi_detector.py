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

# FDI Mapping Utilities
# Quadrant 1: 11..18 -> cls 0..7
# Quadrant 2: 21..28 -> cls 8..15
# Quadrant 3: 31..38 -> cls 16..23
# Quadrant 4: 41..48 -> cls 24..31

def get_fdi_classes():
    fdi_classes = []
    class_id_to_fdi = {}
    fdi_to_class_id = {}
    for q in range(1, 5):
        for p in range(1, 9):
            fdi_num = q * 10 + p
            cls_idx = (q - 1) * 8 + (p - 1)
            fdi_classes.append(f"FDI_{fdi_num}")
            class_id_to_fdi[cls_idx] = fdi_num
            fdi_to_class_id[fdi_num] = cls_idx
    return fdi_classes, class_id_to_fdi, fdi_to_class_id

def swap_fdi_label(cls_idx: int) -> int:
    """Swaps FDI class index horizontally: Q1 <-> Q2, Q4 <-> Q3, keeping tooth position."""
    q = (cls_idx // 8) + 1
    p = (cls_idx % 8) + 1
    if q == 1:
        new_q = 2
    elif q == 2:
        new_q = 1
    elif q == 3:
        new_q = 4
    elif q == 4:
        new_q = 3
    else:
        raise ValueError(f"Invalid quadrant {q}")
    return (new_q - 1) * 8 + (p - 1)

def compute_box_iou(box1, box2):
    # box: [x1, y1, x2, y2]
    xx1 = max(box1[0], box2[0])
    yy1 = max(box1[1], box2[1])
    xx2 = min(box1[2], box2[2])
    yy2 = min(box1[3], box2[3])
    inter_w = max(0.0, xx2 - xx1)
    inter_h = max(0.0, yy2 - yy1)
    inter = inter_w * inter_h
    a1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    a2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0

def apply_fdi_deduplication(proposals):
    """Deterministic post-processing: each FDI number appears at most once per image.
    When duplicate predictions occur for the same FDI number (e.g. 11/21 central incisors),
    keep the one with the highest confidence score.
    """
    by_fdi = {}
    for p in sorted(proposals, key=lambda x: x["confidence"], reverse=True):
        fdi = p["pred_fdi"]
        if fdi not in by_fdi:
            by_fdi[fdi] = p
    return list(by_fdi.values())

def prepare_splits():
    print("=" * 80)
    print("STEP 1: PREPARING 70/15/15 TRAIN/VAL/TEST SPLITS WITH FLIP LABEL SWAPPING")
    print("=" * 80)
    
    json_path = PROJECT_ROOT / "datasets" / "dentex" / "raw" / "training" / "training_data" / "quadrant_enumeration" / "train_quadrant_enumeration.json"
    with open(json_path, "r", encoding="utf-8") as f:
        coco = json.load(f)
        
    xrays_dir = PROJECT_ROOT / "datasets" / "dentex" / "raw" / "training" / "training_data" / "quadrant_enumeration" / "xrays"
    fdi_classes, class_id_to_fdi, fdi_to_class_id = get_fdi_classes()
    
    anns_by_img = defaultdict(list)
    for a in coco["annotations"]:
        anns_by_img[a["image_id"]].append(a)
        
    images = sorted(coco["images"], key=lambda x: x["id"])
    rng = random.Random(42)
    rng.shuffle(images)
    
    total_imgs = len(images)
    n_train = int(total_imgs * 0.70)  # 443
    n_val = int(total_imgs * 0.15)    # 95
    n_test = total_imgs - n_train - n_val # 96
    
    train_images = images[:n_train]
    val_images = images[n_train:n_train + n_val]
    test_images = images[n_train + n_val:]
    
    print(f"Total DENTEX images: {total_imgs}")
    print(f"Train split: {len(train_images)} images (70.0%)")
    print(f"Val split:   {len(val_images)} images (15.0%)")
    print(f"Test split:  {len(test_images)} images (15.0%)")
    
    storage_root = Path("C:/dentrace_storage/datasets/dentex_fdi_701515")
    storage_root.mkdir(parents=True, exist_ok=True)
    
    for split in ["train", "val", "test"]:
        (storage_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (storage_root / "labels" / split).mkdir(parents=True, exist_ok=True)
        
    def write_images_and_labels(img_list, split_name, augment_flip=False):
        written_count = 0
        for idx, im in enumerate(img_list):
            fn = im["file_name"]
            src_img_p = xrays_dir / fn
            dst_img_p = storage_root / "images" / split_name / fn
            
            # Fast copy original
            if not dst_img_p.exists():
                shutil.copy2(src_img_p, dst_img_p)
            written_count += 1
            
            w = float(im["width"])
            h = float(im["height"])
            
            lines_orig = []
            lines_flipped = []
            for a in anns_by_img[im["id"]]:
                q = a["category_id_1"]
                p = a["category_id_2"]
                cls_id = q * 8 + p
                
                bx, by, bw, bh = a["bbox"]
                cx = (bx + bw / 2.0) / w
                cy = (by + bh / 2.0) / h
                nw = bw / w
                nh = bh / h
                
                cx = max(0.0, min(1.0, cx))
                cy = max(0.0, min(1.0, cy))
                nw = max(0.0, min(1.0, nw))
                nh = max(0.0, min(1.0, nh))
                
                lines_orig.append(f"{cls_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
                
                if augment_flip:
                    swapped_cls = swap_fdi_label(cls_id)
                    flipped_cx = 1.0 - cx
                    lines_flipped.append(f"{swapped_cls} {flipped_cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
                    
            label_p = storage_root / "labels" / split_name / (Path(fn).stem + ".txt")
            label_p.write_text("\n".join(lines_orig), encoding="utf-8")
            
            if augment_flip:
                flip_fn = Path(fn).stem + "_flip.png"
                dst_flip_img = storage_root / "images" / split_name / flip_fn
                if not dst_flip_img.exists():
                    with Image.open(src_img_p) as pil_img:
                        img_flipped = pil_img.convert("RGB").transpose(Image.FLIP_LEFT_RIGHT)
                        img_flipped.save(dst_flip_img, compress_level=1)
                written_count += 1
                
                flip_lbl_p = storage_root / "labels" / split_name / (Path(fn).stem + "_flip.txt")
                flip_lbl_p.write_text("\n".join(lines_flipped), encoding="utf-8")
                
            if (idx + 1) % 50 == 0 or idx == len(img_list) - 1:
                print(f"[{split_name}] Processed {idx+1}/{len(img_list)} images...", flush=True)
                
        return written_count

    print("Writing training set (with horizontal flip + FDI label swapping)...", flush=True)
    n_train_written = write_images_and_labels(train_images, "train", augment_flip=True)
    print(f"Train split total images: {n_train_written}", flush=True)
    
    print("Writing validation set...", flush=True)
    n_val_written = write_images_and_labels(val_images, "val", augment_flip=False)
    print(f"Val split total images: {n_val_written}", flush=True)
    
    print("Writing test set...", flush=True)
    n_test_written = write_images_and_labels(test_images, "test", augment_flip=False)
    print(f"Test split total images: {n_test_written}", flush=True)
    
    data_yaml = {
        "path": str(storage_root.resolve()).replace("\\", "/"),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {i: name for i, name in enumerate(fdi_classes)},
        "nc": 32,
        "description": "DENTEX 32-tooth FDI numbering dataset (70/15/15 with FDI-swapped flip augmentation)"
    }
    
    yaml_path = storage_root / "data.yaml"
    import yaml
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data_yaml, f, sort_keys=False)
        
    print(f"Dataset YAML written to {yaml_path}", flush=True)
    return yaml_path, test_images, anns_by_img

def evaluate_model_on_test(model_path_or_yolo, test_images, anns_by_img, is_onnx=False):
    """Evaluates a model (PyTorch YOLO or ONNX) on the held-out test split at IoU 0.4."""
    import onnxruntime as ort
    from ultralytics import YOLO
    
    fdi_classes, class_id_to_fdi, fdi_to_class_id = get_fdi_classes()
    storage_root = Path("C:/dentrace_storage/datasets/dentex_fdi_701515")
    
    if is_onnx:
        sess = ort.InferenceSession(str(model_path_or_yolo), providers=["CPUExecutionProvider"])
        inp_name = sess.get_inputs()[0].name
    else:
        yolo_model = YOLO(str(model_path_or_yolo))
        
    # We will evaluate both BEFORE and AFTER post-processing (deduplication)
    def run_eval(with_dedup: bool):
        total_gt = 0
        detected = 0
        exact_correct = 0
        quad_correct = 0
        pos_correct = 0
        
        quad_total = defaultdict(int)
        quad_correct_by_q = defaultdict(int)
        pos_total = defaultdict(int)
        pos_correct_by_p = defaultdict(int)
        
        for im in test_images:
            img_p = storage_root / "images" / "test" / im["file_name"]
            gt_anns = anns_by_img[im["id"]]
            w, h = float(im["width"]), float(im["height"])
            
            # Ground truth teeth
            gt_teeth = []
            for a in gt_anns:
                bx, by, bw, bh = a["bbox"]
                q = a["category_id_1"] + 1
                pos = a["category_id_2"] + 1
                fdi = q * 10 + pos
                gt_teeth.append({
                    "bbox": [bx, by, bx + bw, by + bh],
                    "fdi": fdi,
                    "quadrant": q,
                    "position": pos,
                    "matched": False
                })
            total_gt += len(gt_teeth)
            
            # Predict proposals
            raw_proposals = []
            if is_onnx:
                # Preprocess for ONNX (640x640 letterbox)
                with Image.open(img_p) as pil_img:
                    orig_img = pil_img.convert("RGB")
                    orig_w, orig_h = orig_img.size
                    
                # Letterbox to 640x640
                scale = min(640.0 / orig_w, 640.0 / orig_h)
                nw, nh = int(round(orig_w * scale)), int(round(orig_h * scale))
                resized = orig_img.resize((nw, nh), Image.BILINEAR)
                
                canvas = Image.new("RGB", (640, 640), (114, 114, 114))
                dx = (640 - nw) // 2
                dy = (640 - nh) // 2
                canvas.paste(resized, (dx, dy))
                
                arr = np.array(canvas, dtype=np.float32) / 255.0
                tensor = np.transpose(arr, (2, 0, 1))[np.newaxis, ...]
                
                out0 = sess.run(None, {inp_name: tensor})[0]
                if out0.ndim == 3 and out0.shape[1] == 36:
                    out0 = np.transpose(out0, (0, 2, 1))
                preds = out0[0]
                
                boxes = preds[:, :4]
                scores_all = preds[:, 4:]
                
                cls_ids = np.argmax(scores_all, axis=1)
                confs = np.max(scores_all, axis=1)
                
                mask = confs >= 0.25
                boxes = boxes[mask]
                confs = confs[mask]
                cls_ids = cls_ids[mask]
                
                if len(boxes) > 0:
                    import torchvision.ops as ops
                    x1 = boxes[:, 0] - boxes[:, 2] / 2.0
                    y1 = boxes[:, 1] - boxes[:, 3] / 2.0
                    x2 = boxes[:, 0] + boxes[:, 2] / 2.0
                    y2 = boxes[:, 1] + boxes[:, 3] / 2.0
                    t_boxes = torch.tensor(np.stack([x1, y1, x2, y2], axis=1), dtype=torch.float32)
                    t_confs = torch.tensor(confs, dtype=torch.float32)
                    keep = ops.nms(t_boxes, t_confs, iou_threshold=0.45).numpy()
                    
                    for k in keep:
                        bx1 = float(max(0.0, (x1[k] - dx) / scale))
                        by1 = float(max(0.0, (y1[k] - dy) / scale))
                        bx2 = float(min(orig_w, (x2[k] - dx) / scale))
                        by2 = float(min(orig_h, (y2[k] - dy) / scale))
                        c_id = int(cls_ids[k])
                        fdi = class_id_to_fdi.get(c_id, 0)
                        raw_proposals.append({
                            "bbox": [bx1, by1, bx2, by2],
                            "confidence": float(confs[k]),
                            "pred_fdi": fdi
                        })
            else:
                # YOLOv8 predict directly
                results = yolo_model.predict(source=str(img_p), conf=0.25, iou=0.45, imgsz=960, verbose=False)
                res = results[0]
                if res.boxes is not None:
                    b_coords = res.boxes.xyxy.cpu().numpy()
                    b_confs = res.boxes.conf.cpu().numpy()
                    b_cls = res.boxes.cls.cpu().numpy()
                    for b, c, cl in zip(b_coords, b_confs, b_cls):
                        c_id = int(cl)
                        fdi = class_id_to_fdi.get(c_id, 0)
                        raw_proposals.append({
                            "bbox": [float(b[0]), float(b[1]), float(b[2]), float(b[3])],
                            "confidence": float(c),
                            "pred_fdi": fdi
                        })
                        
            # Apply deduplication post-processing if requested
            if with_dedup:
                final_proposals = apply_fdi_deduplication(raw_proposals)
            else:
                final_proposals = raw_proposals
                
            # Match to GT teeth at IoU >= 0.4
            for p in final_proposals:
                pred_box = p["bbox"]
                pred_fdi = p["pred_fdi"]
                pred_q = pred_fdi // 10
                pred_pos = pred_fdi % 10
                
                best_iou = 0.0
                best_gt = None
                for gt in gt_teeth:
                    if gt["matched"]:
                        continue
                    iou = compute_box_iou(pred_box, gt["bbox"])
                    if iou > best_iou:
                        best_iou = iou
                        best_gt = gt
                        
                if best_gt is not None and best_iou >= 0.4:
                    best_gt["matched"] = True
                    detected += 1
                    
                    is_exact = (pred_fdi == best_gt["fdi"])
                    is_quad = (pred_q == best_gt["quadrant"])
                    is_pos = (pred_pos == best_gt["position"])
                    
                    if is_exact:
                        exact_correct += 1
                    if is_quad:
                        quad_correct += 1
                    if is_pos:
                        pos_correct += 1
                        
                    quad_total[best_gt["quadrant"]] += 1
                    if is_quad:
                        quad_correct_by_q[best_gt["quadrant"]] += 1
                        
                    pos_total[best_gt["position"]] += 1
                    if is_pos:
                        pos_correct_by_p[best_gt["position"]] += 1
                        
        recall_pct = (detected / total_gt) * 100.0 if total_gt > 0 else 0.0
        matched_acc = (exact_correct / detected) * 100.0 if detected > 0 else 0.0
        e2e_acc = (exact_correct / total_gt) * 100.0 if total_gt > 0 else 0.0
        quad_acc = (quad_correct / detected) * 100.0 if detected > 0 else 0.0
        pos_acc = (pos_correct / detected) * 100.0 if detected > 0 else 0.0
        
        quad_breakdown = {
            f"Quadrant_{q}": round((quad_correct_by_q[q] / max(1, quad_total[q])) * 100.0, 2)
            for q in range(1, 5)
        }
        pos_breakdown = {
            f"Position_{p}": round((pos_correct_by_p[p] / max(1, pos_total[p])) * 100.0, 2)
            for p in range(1, 9)
        }
        
        return {
            "total_gt": total_gt,
            "detected": detected,
            "exact_correct": exact_correct,
            "recall_iou04": round(recall_pct, 2),
            "matched_exact_fdi_acc": round(matched_acc, 2),
            "e2e_exact_fdi_acc": round(e2e_acc, 2),
            "quadrant_accuracy": round(quad_acc, 2),
            "position_accuracy": round(pos_acc, 2),
            "quad_breakdown": quad_breakdown,
            "pos_breakdown": pos_breakdown,
        }
        
    res_before = run_eval(with_dedup=False)
    res_after = run_eval(with_dedup=True)
    return {"before_post_processing": res_before, "after_post_processing": res_after}

def train_and_evaluate():
    yaml_path, test_images, anns_by_img = prepare_splits()
    
    print("\n" + "=" * 80)
    print("STEP 2: EVALUATING BASELINE MODEL (dentex_fdi_yolov8n_best.onnx) ON TEST SPLIT")
    print("=" * 80)
    baseline_onnx = PROJECT_ROOT / "ml" / "models" / "checkpoints" / "dentex_fdi_yolov8n_best.onnx"
    baseline_eval = evaluate_model_on_test(baseline_onnx, test_images, anns_by_img, is_onnx=True)
    print("BASELINE ON TEST SPLIT (96 images, 2,714 GT teeth):")
    print(f"  Before Post-Processing: Recall: {baseline_eval['before_post_processing']['recall_iou04']}% | Matched Acc: {baseline_eval['before_post_processing']['matched_exact_fdi_acc']}% | E2E Acc: {baseline_eval['before_post_processing']['e2e_exact_fdi_acc']}%")
    print(f"  After Post-Processing:  Recall: {baseline_eval['after_post_processing']['recall_iou04']}% | Matched Acc: {baseline_eval['after_post_processing']['matched_exact_fdi_acc']}% | E2E Acc: {baseline_eval['after_post_processing']['e2e_exact_fdi_acc']}%")
    
    print("\n" + "=" * 80)
    print("STEP 3: TRAINING IMPROVED 32-CLASS FDI DETECTOR (YOLOv8s, imgsz 960, 80 epochs)")
    print("=" * 80)
    
    from ultralytics import YOLO
    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device} (NVIDIA GeForce RTX 2050 4GB VRAM)")
    
    # Store all runs in C:\dentrace_runs to strictly protect D:\
    runs_dir = Path("C:/dentrace_runs/fdi_train")
    runs_dir.mkdir(parents=True, exist_ok=True)
    
    model_choice = "yolov8s.pt"
    batch_size = 4
    imgsz = 960
    
    # Try training yolov8s; fall back to yolov8n if OOM occurs
    try:
        model = YOLO(model_choice)
        t_start = time.perf_counter()
        train_res = model.train(
            data=str(yaml_path),
            epochs=80,
            batch=batch_size,
            imgsz=imgsz,
            device=device,
            seed=42,
            optimizer="AdamW",
            lr0=0.001,
            cos_lr=True,
            patience=15,
            fliplr=0.0,  # Critical: disabled because we pre-augmented flipped images with correct FDI label swapping!
            save=True,
            project=str(runs_dir),
            name="dentex_fdi_yolov8s_960",
            exist_ok=True,
            verbose=True
        )
        t_end = time.perf_counter()
        used_model_name = "yolov8s"
    except Exception as e:
        print(f"YOLOv8s training encountered error: {e}. Falling back to YOLOv8n at imgsz 960, batch 4...")
        model = YOLO("yolov8n.pt")
        t_start = time.perf_counter()
        train_res = model.train(
            data=str(yaml_path),
            epochs=80,
            batch=batch_size,
            imgsz=imgsz,
            device=device,
            seed=42,
            optimizer="AdamW",
            lr0=0.001,
            cos_lr=True,
            patience=15,
            fliplr=0.0,
            save=True,
            project=str(runs_dir),
            name="dentex_fdi_yolov8n_960",
            exist_ok=True,
            verbose=True
        )
        t_end = time.perf_counter()
        used_model_name = "yolov8n"
        
    train_duration_s = t_end - t_start
    print(f"Training completed in {train_duration_s:.1f} s ({train_duration_s/60.0:.2f} min)")
    
    best_pt = Path(model.trainer.best)
    print(f"Best model checkpoint saved at: {best_pt}")
    
    # Export to ONNX
    print("Exporting best checkpoint to ONNX...")
    exported_onnx = model.export(format="onnx", opset=12, simplify=True, dynamic=False, imgsz=imgsz)
    print(f"Exported to: {exported_onnx}")
    
    print("\n" + "=" * 80)
    print("STEP 4: EVALUATING NEW TRAINED MODEL ON HELD-OUT TEST SPLIT (96 images)")
    print("=" * 80)
    new_model_eval = evaluate_model_on_test(best_pt, test_images, anns_by_img, is_onnx=False)
    
    print("NEW MODEL EVALUATION RESULTS ON TEST SPLIT:")
    print("  Before Post-Processing:")
    print(f"    Recall @ IoU 0.4:        {new_model_eval['before_post_processing']['recall_iou04']}%")
    print(f"    Matched Exact FDI Acc:   {new_model_eval['before_post_processing']['matched_exact_fdi_acc']}%")
    print(f"    End-to-End Exact FDI Acc:{new_model_eval['before_post_processing']['e2e_exact_fdi_acc']}%")
    print(f"    Quadrant Accuracy:       {new_model_eval['before_post_processing']['quadrant_accuracy']}%")
    print(f"    Position Accuracy:       {new_model_eval['before_post_processing']['position_accuracy']}%")
    print("  After Post-Processing (Deduplication):")
    print(f"    Recall @ IoU 0.4:        {new_model_eval['after_post_processing']['recall_iou04']}%")
    print(f"    Matched Exact FDI Acc:   {new_model_eval['after_post_processing']['matched_exact_fdi_acc']}%")
    print(f"    End-to-End Exact FDI Acc:{new_model_eval['after_post_processing']['e2e_exact_fdi_acc']}%")
    print(f"    Quadrant Accuracy:       {new_model_eval['after_post_processing']['quadrant_accuracy']}%")
    print(f"    Position Accuracy:       {new_model_eval['after_post_processing']['position_accuracy']}%")
    
    # Adoption Decision
    old_e2e = baseline_eval['after_post_processing']['e2e_exact_fdi_acc']
    new_e2e = new_model_eval['after_post_processing']['e2e_exact_fdi_acc']
    
    print("\n" + "=" * 80)
    print(f"ADOPTION COMPARISON: Baseline E2E={old_e2e}% vs New E2E={new_e2e}%")
    print("=" * 80)
    
    adopted = False
    if new_e2e > old_e2e:
        print(f"ADOPTED: New model beats baseline on held-out test split ({new_e2e}% > {old_e2e}%)!")
        target_onnx = PROJECT_ROOT / "ml" / "models" / "checkpoints" / "dentex_fdi_improved.onnx"
        shutil.copy2(exported_onnx, target_onnx)
        adopted = True
    else:
        print(f"RETAINED BASELINE: New model did not beat baseline on held-out test split ({new_e2e}% <= {old_e2e}%).")
        
    full_report = {
        "architecture_used": used_model_name,
        "imgsz": imgsz,
        "batch_size": batch_size,
        "epochs_requested": 80,
        "training_time_s": round(train_duration_s, 2),
        "best_checkpoint": str(best_pt),
        "exported_onnx": str(exported_onnx),
        "adopted": adopted,
        "baseline_test_eval": baseline_eval,
        "new_model_test_eval": new_model_eval,
    }
    
    report_p = PROJECT_ROOT / "scratch" / "task1_improved_fdi_results.json"
    with open(report_p, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)
    print(f"Wrote full report to: {report_p}")

if __name__ == "__main__":
    train_and_evaluate()
