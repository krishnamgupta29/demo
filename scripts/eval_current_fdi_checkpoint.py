import json
import sys
import time
from collections import defaultdict
from pathlib import Path
import numpy as np
import torch
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO

def get_fdi_classes():
    fdi_classes = []
    class_id_to_fdi = {}
    for q in range(1, 5):
        for p in range(1, 9):
            fdi_num = q * 10 + p
            cls_idx = (q - 1) * 8 + (p - 1)
            fdi_classes.append(f"FDI_{fdi_num}")
            class_id_to_fdi[cls_idx] = fdi_num
    return fdi_classes, class_id_to_fdi

def compute_box_iou(box1, box2):
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
    by_fdi = {}
    for p in sorted(proposals, key=lambda x: x["confidence"], reverse=True):
        fdi = p["pred_fdi"]
        if fdi not in by_fdi:
            by_fdi[fdi] = p
    return list(by_fdi.values())

def main():
    print("=" * 80)
    print("EVALUATING CURRENT YOLOv8s BEST CHECKPOINT ON HELD-OUT TEST SPLIT (96 images)")
    print("=" * 80)
    
    ckpt_path = Path("C:/dentrace_runs/fdi_train/dentex_fdi_yolov8s_960/weights/best.pt")
    if not ckpt_path.exists():
        print(f"Checkpoint not found: {ckpt_path}")
        return
        
    model = YOLO(str(ckpt_path))
    _, class_id_to_fdi = get_fdi_classes()
    
    json_path = PROJECT_ROOT / "datasets" / "dentex" / "raw" / "training" / "training_data" / "quadrant_enumeration" / "train_quadrant_enumeration.json"
    with open(json_path, "r", encoding="utf-8") as f:
        coco = json.load(f)
        
    storage_root = Path("C:/dentrace_storage/datasets/dentex_fdi_701515")
    test_img_dir = storage_root / "images" / "test"
    test_filenames = {p.name for p in test_img_dir.glob("*.png")}
    
    test_images = [im for im in coco["images"] if im["file_name"] in test_filenames]
    anns_by_img = defaultdict(list)
    for a in coco["annotations"]:
        anns_by_img[a["image_id"]].append(a)
        
    print(f"Found {len(test_images)} test images matching test directory.")
    
    # Run batch inference on test images
    test_img_paths = [str(storage_root / "images" / "test" / im["file_name"]) for im in test_images]
    print(f"Running inference on {len(test_img_paths)} test images...")
    t0 = time.perf_counter()
    results = model.predict(source=test_img_paths, conf=0.25, iou=0.45, imgsz=960, device=0, verbose=False)
    t1 = time.perf_counter()
    print(f"Inference completed in {t1 - t0:.2f} seconds ({len(test_img_paths)/(t1-t0):.1f} fps).")
    
    # Store proposals per image
    all_raw_proposals = []
    for res in results:
        props = []
        if res.boxes is not None:
            b_coords = res.boxes.xyxy.cpu().numpy()
            b_confs = res.boxes.conf.cpu().numpy()
            b_cls = res.boxes.cls.cpu().numpy()
            for b, c, cl in zip(b_coords, b_confs, b_cls):
                c_id = int(cl)
                fdi = class_id_to_fdi.get(c_id, 0)
                props.append({
                    "bbox": [float(b[0]), float(b[1]), float(b[2]), float(b[3])],
                    "confidence": float(c),
                    "pred_fdi": fdi
                })
        all_raw_proposals.append(props)
        
    def evaluate(with_dedup: bool):
        total_gt = 0
        detected = 0
        exact_correct = 0
        quad_correct = 0
        pos_correct = 0
        
        quad_total = defaultdict(int)
        quad_correct_by_q = defaultdict(int)
        pos_total = defaultdict(int)
        pos_correct_by_p = defaultdict(int)
        
        for im, raw_props in zip(test_images, all_raw_proposals):
            gt_anns = anns_by_img[im["id"]]
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
            
            final_props = apply_fdi_deduplication(raw_props) if with_dedup else raw_props
            
            for p in final_props:
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

    res_before = evaluate(with_dedup=False)
    res_after = evaluate(with_dedup=True)
    
    print("\nRESULTS ON HELD-OUT TEST SPLIT (96 images, 2,714 GT teeth):")
    print("--- BEFORE POST-PROCESSING ---")
    print(f"Detection Recall @ IoU 0.4:      {res_before['recall_iou04']}% ({res_before['detected']}/{res_before['total_gt']})")
    print(f"Matched Exact FDI Accuracy:       {res_before['matched_exact_fdi_acc']}% ({res_before['exact_correct']}/{res_before['detected']})")
    print(f"End-to-End Exact FDI Accuracy:    {res_before['e2e_exact_fdi_acc']}% ({res_before['exact_correct']}/{res_before['total_gt']})")
    print(f"Quadrant Accuracy:                {res_before['quadrant_accuracy']}%")
    print(f"Position Accuracy:                {res_before['position_accuracy']}%")
    print(f"Quadrant Breakdown: {res_before['quad_breakdown']}")
    print(f"Position Breakdown: {res_before['pos_breakdown']}")
    
    print("\n--- AFTER POST-PROCESSING (DEDUPLICATION) ---")
    print(f"Detection Recall @ IoU 0.4:      {res_after['recall_iou04']}% ({res_after['detected']}/{res_after['total_gt']})")
    print(f"Matched Exact FDI Accuracy:       {res_after['matched_exact_fdi_acc']}% ({res_after['exact_correct']}/{res_after['detected']})")
    print(f"End-to-End Exact FDI Accuracy:    {res_after['e2e_exact_fdi_acc']}% ({res_after['exact_correct']}/{res_after['total_gt']})")
    print(f"Quadrant Accuracy:                {res_after['quadrant_accuracy']}%")
    print(f"Position Accuracy:                {res_after['position_accuracy']}%")
    print(f"Quadrant Breakdown: {res_after['quad_breakdown']}")
    print(f"Position Breakdown: {res_after['pos_breakdown']}")

    out_file = PROJECT_ROOT / "scratch" / "task1_interim_test_eval.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"before": res_before, "after": res_after}, f, indent=2)
    print(f"\nSaved evaluation to {out_file}")

if __name__ == "__main__":
    main()
