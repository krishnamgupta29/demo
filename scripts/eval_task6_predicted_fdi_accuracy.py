import json
import sys
import time
from collections import defaultdict
from pathlib import Path
import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.ml.fdi_numbering import FDINumberingEngine
from backend.ml.fdi_solver import CalibratedFDISolver

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

def run_fdi_predicted_eval():
    print("=" * 70)
    print("TASK 6: REAL END-TO-END FDI ACCURACY EVALUATION (PREDICTED BOXES)")
    print("=" * 70)
    
    json_path = PROJECT_ROOT / "datasets" / "dentex" / "raw" / "training" / "training_data" / "quadrant_enumeration" / "train_quadrant_enumeration.json"
    with open(json_path, "r", encoding="utf-8") as f:
        coco = json.load(f)
        
    img_name_to_id = {im["file_name"]: im["id"] for im in coco["images"]}
    id_to_anns = defaultdict(list)
    for a in coco["annotations"]:
        id_to_anns[a["image_id"]].append(a)
        
    val_dir = PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val"
    val_image_paths = sorted(list(val_dir.glob("*.png")))
    
    # Filter to images that have ground truth in quadrant_enumeration.json
    eval_images = [p for p in val_image_paths if p.name in img_name_to_id]
    print(f"Total DENTEX validation images: {len(val_image_paths)}")
    print(f"Validation images with ground truth enumeration: {len(eval_images)}")
    print("Note on potential data leakage: 'dental_fdi.onnx' was sourced from abychkov/dental-fdi-detection on HuggingFace.")
    print("Its training/test split membership is unconfirmed; evaluation performed on our DENTEX val split (124 images).")
    print("-" * 70)
    
    engine = FDINumberingEngine()
    solver = CalibratedFDISolver()
    
    # Metrics
    total_gt_teeth = 0
    matched_gt_teeth = 0
    
    correct_exact_fdi = 0
    correct_quadrant = 0
    correct_position = 0
    
    # Per-quadrant tracking
    quadrant_total = defaultdict(int)
    quadrant_correct = defaultdict(int)
    
    # Per-position tracking (1-8)
    position_total = defaultdict(int)
    position_correct = defaultdict(int)
    
    latencies = []
    
    start_time = time.perf_counter()
    
    for idx, img_p in enumerate(eval_images):
        img_id = img_name_to_id[img_p.name]
        gt_anns = id_to_anns[img_id]
        
        # Ground truth teeth list: [box, gt_fdi, gt_q, gt_pos]
        gt_teeth = []
        for a in gt_anns:
            b = a["bbox"]  # [x, y, w, h]
            gt_box = [b[0], b[1], b[0] + b[2], b[1] + b[3]]
            gt_q = a["category_id_1"] + 1
            gt_pos = a["category_id_2"] + 1
            gt_fdi = gt_q * 10 + gt_pos
            gt_teeth.append({
                "bbox": gt_box,
                "fdi": gt_fdi,
                "quadrant": gt_q,
                "position": gt_pos,
                "matched": False
            })
            
        total_gt_teeth += len(gt_teeth)
        
        with Image.open(img_p) as pil_img:
            img = pil_img.convert("RGB")
            
        t0 = time.perf_counter()
        fdi_res = engine.predict_teeth(img)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)
        
        predicted_teeth = fdi_res.get("teeth", [])
        
        # Format raw proposals for CalibratedFDISolver
        raw_props = [
            {
                "id": f"prop_{i}",
                "bbox": t.bbox_orig,
                "confidence": t.confidence,
            }
            for i, t in enumerate(predicted_teeth)
        ]
        
        resolved_teeth = solver.solve(
            raw_props,
            image_width=img.width,
            image_height=img.height,
        )
        
        # Match resolved predictions to GT by IoU >= 0.4
        for rt in resolved_teeth:
            if rt.fdi_number is None:
                continue
            pred_box = rt.bbox
            pred_fdi = rt.fdi_number
            pred_q = pred_fdi // 10
            pred_pos = pred_fdi % 10
            
            # Find best overlapping GT tooth
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
                matched_gt_teeth += 1
                
                # Check accuracies
                is_exact = (pred_fdi == best_gt["fdi"])
                is_quad = (pred_q == best_gt["quadrant"])
                is_pos = (pred_pos == best_gt["position"])
                
                if is_exact:
                    correct_exact_fdi += 1
                if is_quad:
                    correct_quadrant += 1
                if is_pos:
                    correct_position += 1
                    
                quadrant_total[best_gt["quadrant"]] += 1
                if is_quad:
                    quadrant_correct[best_gt["quadrant"]] += 1
                    
                position_total[best_gt["position"]] += 1
                if is_pos:
                    position_correct[best_gt["position"]] += 1
                    
        if (idx + 1) % 25 == 0 or idx == len(eval_images) - 1:
            print(f"Processed [{idx+1}/{len(eval_images)}] images... Current exact-FDI on matched: {correct_exact_fdi}/{matched_gt_teeth} ({correct_exact_fdi/max(1, matched_gt_teeth)*100:.2f}%)")

    total_eval_time = time.perf_counter() - start_time
    
    # Calculate metrics
    detection_recall = (matched_gt_teeth / total_gt_teeth) * 100.0 if total_gt_teeth > 0 else 0.0
    exact_fdi_on_matched = (correct_exact_fdi / matched_gt_teeth) * 100.0 if matched_gt_teeth > 0 else 0.0
    exact_fdi_end_to_end = (correct_exact_fdi / total_gt_teeth) * 100.0 if total_gt_teeth > 0 else 0.0
    
    quadrant_acc_on_matched = (correct_quadrant / matched_gt_teeth) * 100.0 if matched_gt_teeth > 0 else 0.0
    position_acc_on_matched = (correct_position / matched_gt_teeth) * 100.0 if matched_gt_teeth > 0 else 0.0

    print("\n" + "=" * 70)
    print("TASK 6 FINAL MEASURED RESULTS:")
    print("=" * 70)
    print(f"Validation Images Evaluated: {len(eval_images)}")
    print(f"Total Ground-Truth Teeth: {total_gt_teeth}")
    print(f"Teeth Detected & Matched (IoU >= 0.4): {matched_gt_teeth} ({detection_recall:.2f}% recall)")
    print(f"\n1. Exact-FDI Accuracy (on detected/matched teeth): {exact_fdi_on_matched:.2f}% ({correct_exact_fdi}/{matched_gt_teeth})")
    print(f"   Exact-FDI Accuracy (end-to-end on all GT teeth): {exact_fdi_end_to_end:.2f}% ({correct_exact_fdi}/{total_gt_teeth})")
    print(f"2. Quadrant Accuracy (on detected/matched teeth): {quadrant_acc_on_matched:.2f}% ({correct_quadrant}/{matched_gt_teeth})")
    print(f"3. Per-Position Accuracy (on detected/matched teeth): {position_acc_on_matched:.2f}% ({correct_position}/{matched_gt_teeth})")
    
    print("\n--- Quadrant Accuracy Breakdown ---")
    quad_names = {1: "Q1 (Maxillary Right)", 2: "Q2 (Maxillary Left)", 3: "Q3 (Mandibular Left)", 4: "Q4 (Mandibular Right)"}
    for q in sorted(quadrant_total.keys()):
        tot = quadrant_total[q]
        cor = quadrant_correct[q]
        acc = (cor / tot) * 100.0 if tot > 0 else 0.0
        print(f"  {quad_names.get(q, f'Q{q}')}: {acc:.2f}% ({cor}/{tot})")
        
    print("\n--- Per-Position Accuracy Breakdown (1: Central Incisor -> 8: Wisdom Molar) ---")
    pos_names = {
        1: "Central Incisor", 2: "Lateral Incisor", 3: "Canine", 4: "1st Premolar",
        5: "2nd Premolar", 6: "1st Molar", 7: "2nd Molar", 8: "3rd Molar"
    }
    for p in sorted(position_total.keys()):
        tot = position_total[p]
        cor = position_correct[p]
        acc = (cor / tot) * 100.0 if tot > 0 else 0.0
        print(f"  Position {p} ({pos_names.get(p, '')}): {acc:.2f}% ({cor}/{tot})")
        
    results_summary = {
        "images_evaluated": len(eval_images),
        "total_gt_teeth": total_gt_teeth,
        "matched_gt_teeth": matched_gt_teeth,
        "detection_recall_pct": round(detection_recall, 2),
        "exact_fdi_matched_pct": round(exact_fdi_on_matched, 2),
        "exact_fdi_end_to_end_pct": round(exact_fdi_end_to_end, 2),
        "quadrant_acc_matched_pct": round(quadrant_acc_on_matched, 2),
        "position_acc_matched_pct": round(position_acc_on_matched, 2),
        "per_quadrant": {quad_names.get(q, str(q)): round((quadrant_correct[q]/quadrant_total[q])*100.0, 2) for q in quadrant_total},
        "per_position": {f"Pos_{p}_{pos_names.get(p, '')}": round((position_correct[p]/position_total[p])*100.0, 2) for p in position_total},
        "latency_mean_ms": round(float(np.mean(latencies)), 2),
        "latency_median_ms": round(float(np.median(latencies)), 2),
        "latency_p95_ms": round(float(np.percentile(latencies, 95)), 2),
    }
    
    out_file = PROJECT_ROOT / "scratch" / "task6_fdi_predicted_eval_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2)
    print(f"\nWrote results summary to: {out_file}")

if __name__ == "__main__":
    run_fdi_predicted_eval()
