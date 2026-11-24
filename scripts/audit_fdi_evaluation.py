import json
import sys
import time
from collections import defaultdict
from pathlib import Path
import numpy as np
import onnxruntime as ort
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.ml.preprocessor import ImagePreprocessor
from backend.ml.fdi_solver import CalibratedFDISolver

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

def class_idx_to_fdi(class_idx: int) -> int:
    quadrant = (class_idx // 8) + 1
    tooth_pos = (class_idx % 8) + 1
    return quadrant * 10 + tooth_pos

def run_fdi_audit():
    print("=" * 80)
    print("TASK A: FDI DETECTION & EVALUATION AUDIT")
    print("=" * 80)
    
    json_path = PROJECT_ROOT / "datasets" / "dentex" / "raw" / "training" / "training_data" / "quadrant_enumeration" / "train_quadrant_enumeration.json"
    with open(json_path, "r", encoding="utf-8") as f:
        coco = json.load(f)
        
    img_name_to_id = {im["file_name"]: im["id"] for im in coco["images"]}
    id_to_anns = defaultdict(list)
    for a in coco["annotations"]:
        id_to_anns[a["image_id"]].append(a)
        
    val_dir = PROJECT_ROOT / "ml" / "datasets" / "dentex" / "yolo_seg" / "images" / "val"
    val_image_paths = sorted(list(val_dir.glob("*.png")))
    eval_images = [p for p in val_image_paths if p.name in img_name_to_id]
    
    print(f"Validation images with ground truth enumeration: {len(eval_images)}")
    
    onnx_path = PROJECT_ROOT / "ml" / "models" / "checkpoints" / "dental_fdi.onnx"
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    inp_name = sess.get_inputs()[0].name
    
    solver = CalibratedFDISolver(enable_abstention=False)  # Non-abstaining for full recall comparison
    solver_with_abstain = CalibratedFDISolver(enable_abstention=True)
    
    # We will test multiple IoU matching thresholds: 0.3, 0.4, 0.5
    iou_thresh_list = [0.3, 0.4, 0.5]
    
    # Metrics containers
    # For each IoU threshold:
    # gt_total
    # matched_detected (raw detection recall)
    # correct_fdi_strat_a (detector's own predicted class)
    # correct_fdi_strat_b (CalibratedFDISolver ordering without abstention)
    # correct_fdi_strat_b_abstain (CalibratedFDISolver with abstention)
    results = {
        thresh: {
            "gt_total": 0,
            "detected": 0,
            "correct_a": 0,
            "correct_b": 0,
            "correct_b_abstain": 0,
            "abstain_count": 0,
        }
        for thresh in iou_thresh_list
    }
    
    # Per quadrant and position counters for Best Strategy at IoU 0.4
    quad_total = defaultdict(int)
    quad_correct_a = defaultdict(int)
    pos_total = defaultdict(int)
    pos_correct_a = defaultdict(int)
    
    t0_all = time.perf_counter()
    
    for idx, img_p in enumerate(eval_images):
        img_id = img_name_to_id[img_p.name]
        gt_anns = id_to_anns[img_id]
        
        gt_teeth_base = []
        for a in gt_anns:
            b = a["bbox"]
            gt_box = [b[0], b[1], b[0] + b[2], b[1] + b[3]]
            gt_q = a["category_id_1"] + 1
            gt_pos = a["category_id_2"] + 1
            gt_fdi = gt_q * 10 + gt_pos
            gt_teeth_base.append({
                "bbox": gt_box,
                "fdi": gt_fdi,
                "quadrant": gt_q,
                "position": gt_pos,
            })
            
        with Image.open(img_p) as pil_img:
            img = pil_img.convert("RGB")
        orig_w, orig_h = img.size
        
        # Inference
        tensor, meta = ImagePreprocessor.letterbox(img, target_size=640)
        outputs = sess.run(None, {inp_name: tensor})
        proposals = outputs[0][0]  # shape (300, 36)
        coords = proposals[:, :4]
        class_scores = proposals[:, 4:]  # 32 classes
        
        max_scores = np.max(class_scores, axis=1)
        argmax_classes = np.argmax(class_scores, axis=1)
        
        # Filter confidence >= 0.30
        cand_idx = np.where(max_scores >= 0.30)[0]
        # SORT by confidence descending (CRITICAL BUG FIX)
        cand_idx = cand_idx[np.argsort(-max_scores[cand_idx])]
        
        # Score-sorted NMS
        kept_proposals = []
        seen_boxes = []
        for ci in cand_idx:
            sc = float(max_scores[ci])
            cls_i = int(argmax_classes[ci])
            cx, cy, w, h = coords[ci]
            
            x1_lb = (cx - w / 2.0) * meta.target_size
            y1_lb = (cy - h / 2.0) * meta.target_size
            x2_lb = (cx + w / 2.0) * meta.target_size
            y2_lb = (cy + h / 2.0) * meta.target_size
            
            box_orig = ImagePreprocessor.unletterbox_box([x1_lb, y1_lb, x2_lb, y2_lb], meta)
            
            # IoU deduplication
            dup = False
            for sb in seen_boxes:
                if compute_box_iou(box_orig, sb) > 0.45:
                    dup = True
                    break
            if dup:
                continue
            seen_boxes.append(box_orig)
            
            pred_fdi = class_idx_to_fdi(cls_i)
            kept_proposals.append({
                "id": f"prop_{len(kept_proposals)}",
                "bbox": box_orig,
                "confidence": sc,
                "pred_fdi_detector": pred_fdi,
                "cls_idx": cls_i
            })
            
        # Strategy (b): FDISolver on these predicted boxes
        resolved_b = solver.solve(
            [{"id": p["id"], "bbox": p["bbox"], "confidence": p["confidence"]} for p in kept_proposals],
            image_width=orig_w,
            image_height=orig_h
        )
        b_fdi_by_id = {rt.tooth_id: rt.fdi_number for rt in resolved_b}
        
        # Strategy (b) with abstention
        resolved_b_abs = solver_with_abstain.solve(
            [{"id": p["id"], "bbox": p["bbox"], "confidence": p["confidence"]} for p in kept_proposals],
            image_width=orig_w,
            image_height=orig_h
        )
        b_abs_fdi_by_id = {rt.tooth_id: rt.fdi_number for rt in resolved_b_abs}
        
        for p in kept_proposals:
            p["pred_fdi_solver"] = b_fdi_by_id.get(p["id"])
            p["pred_fdi_solver_abs"] = b_abs_fdi_by_id.get(p["id"])
            
        # Evaluate for each IoU threshold
        for match_iou_th in iou_thresh_list:
            res_th = results[match_iou_th]
            res_th["gt_total"] += len(gt_teeth_base)
            
            gt_matched = [False] * len(gt_teeth_base)
            
            for p in kept_proposals:
                pred_box = p["bbox"]
                fdi_a = p["pred_fdi_detector"]
                fdi_b = p["pred_fdi_solver"]
                fdi_b_abs = p["pred_fdi_solver_abs"]
                
                # Match to GT
                best_iou = 0.0
                best_gt_idx = None
                for g_i, gt in enumerate(gt_teeth_base):
                    if gt_matched[g_i]:
                        continue
                    iou = compute_box_iou(pred_box, gt["bbox"])
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = g_i
                        
                if best_gt_idx is not None and best_iou >= match_iou_th:
                    gt_matched[best_gt_idx] = True
                    gt = gt_teeth_base[best_gt_idx]
                    
                    res_th["detected"] += 1
                    
                    if fdi_a == gt["fdi"]:
                        res_th["correct_a"] += 1
                    if fdi_b == gt["fdi"]:
                        res_th["correct_b"] += 1
                    if fdi_b_abs == gt["fdi"]:
                        res_th["correct_b_abstain"] += 1
                    elif fdi_b_abs is None:
                        res_th["abstain_count"] += 1
                        
                    if match_iou_th == 0.4:
                        quad_total[gt["quadrant"]] += 1
                        pos_total[gt["position"]] += 1
                        if fdi_a == gt["fdi"]:
                            quad_correct_a[gt["quadrant"]] += 1
                            pos_correct_a[gt["position"]] += 1
                            
        if (idx + 1) % 25 == 0 or idx == len(eval_images) - 1:
            det4 = results[0.4]["detected"]
            cor_a4 = results[0.4]["correct_a"]
            cor_b4 = results[0.4]["correct_b"]
            gt4 = results[0.4]["gt_total"]
            print(f"[{idx+1:03d}/{len(eval_images)}] IoU 0.4: Det Recall: {det4}/{gt4} ({det4/gt4*100:.1f}%) | Strat (a) Acc: {cor_a4}/{det4} ({cor_a4/max(1,det4)*100:.1f}%) | Strat (b) Acc: {cor_b4}/{det4} ({cor_b4/max(1,det4)*100:.1f}%)")

    total_time = time.perf_counter() - t0_all
    print("-" * 80)
    print("FINAL MEASURED COMPARISON RESULTS:")
    print("-" * 80)
    
    for match_iou_th in iou_thresh_list:
        r = results[match_iou_th]
        gt = r["gt_total"]
        det = r["detected"]
        cor_a = r["correct_a"]
        cor_b = r["correct_b"]
        cor_b_abs = r["correct_b_abstain"]
        
        recall_pct = (det / gt) * 100.0
        acc_a_matched = (cor_a / det) * 100.0 if det > 0 else 0.0
        acc_a_e2e = (cor_a / gt) * 100.0 if gt > 0 else 0.0
        
        acc_b_matched = (cor_b / det) * 100.0 if det > 0 else 0.0
        acc_b_e2e = (cor_b / gt) * 100.0 if gt > 0 else 0.0
        
        acc_b_abs_matched = (cor_b_abs / det) * 100.0 if det > 0 else 0.0
        
        print(f"=== MATCHING IoU >= {match_iou_th:.1f} ===")
        print(f"  • Detection Recall: {recall_pct:.2f}% ({det}/{gt} GT teeth detected)")
        print(f"  • Strategy (a) [Detector's Predicted Class Label]:")
        print(f"      - Exact-FDI Accuracy (on detected/matched teeth): {acc_a_matched:.2f}% ({cor_a}/{det})")
        print(f"      - End-to-End Exact-FDI Accuracy (across all GT): {acc_a_e2e:.2f}% ({cor_a}/{gt})")
        print(f"  • Strategy (b) [CalibratedFDISolver Topological Ordering]:")
        print(f"      - Exact-FDI Accuracy (on detected/matched teeth): {acc_b_matched:.2f}% ({cor_b}/{det})")
        print(f"      - End-to-End Exact-FDI Accuracy (across all GT): {acc_b_e2e:.2f}% ({cor_b}/{gt})")
        print(f"      - CalibratedFDISolver with Abstention Accuracy:  {acc_b_abs_matched:.2f}% ({cor_b_abs}/{det}) [Abstained: {r['abstain_count']}]")
        print()
        
    print("--- Strategy (a) Per-Quadrant Breakdown (IoU >= 0.4) ---")
    quad_names = {1: "Q1 Maxillary Right", 2: "Q2 Maxillary Left", 3: "Q3 Mandibular Left", 4: "Q4 Mandibular Right"}
    for q in sorted(quad_total.keys()):
        tot = quad_total[q]
        cor = quad_correct_a[q]
        print(f"  {quad_names[q]}: {(cor/tot)*100.0:.2f}% ({cor}/{tot})")
        
    print("\n--- Strategy (a) Per-Position Breakdown (IoU >= 0.4) ---")
    for p in sorted(pos_total.keys()):
        tot = pos_total[p]
        cor = pos_correct_a[p]
        print(f"  Position {p}: {(cor/tot)*100.0:.2f}% ({cor}/{tot})")
        
    # Save results to json
    audit_summary = {
        "matching_iou_thresholds": iou_thresh_list,
        "results": {
            str(k): {
                "gt_total": v["gt_total"],
                "detected": v["detected"],
                "detection_recall_pct": round((v["detected"]/v["gt_total"])*100.0, 2),
                "strategy_a_exact_fdi_matched_pct": round((v["correct_a"]/v["detected"])*100.0, 2),
                "strategy_a_exact_fdi_e2e_pct": round((v["correct_a"]/v["gt_total"])*100.0, 2),
                "strategy_b_exact_fdi_matched_pct": round((v["correct_b"]/v["detected"])*100.0, 2),
                "strategy_b_exact_fdi_e2e_pct": round((v["correct_b"]/v["gt_total"])*100.0, 2),
            }
            for k, v in results.items()
        },
        "per_quadrant_strategy_a": {quad_names[q]: round((quad_correct_a[q]/quad_total[q])*100.0, 2) for q in quad_total},
        "per_position_strategy_a": {f"Pos_{p}": round((pos_correct_a[p]/pos_total[p])*100.0, 2) for p in pos_total},
    }
    out_file = PROJECT_ROOT / "scratch" / "task_a_fdi_audit_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)
    print(f"\nWrote full audit to: {out_file}")

if __name__ == "__main__":
    run_fdi_audit()
