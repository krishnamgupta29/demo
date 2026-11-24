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

def evaluate_yolov8n_fdi():
    print("=" * 80)
    print("EVALUATING YOLOV8N 32-CLASS FDI MODEL ON HELD-OUT VAL SPLIT (127 IMAGES)")
    print("=" * 80)

    val_images_dir = PROJECT_ROOT / "ml" / "datasets" / "dentex_fdi" / "images" / "val"
    val_labels_dir = PROJECT_ROOT / "ml" / "datasets" / "dentex_fdi" / "labels" / "val"
    val_image_paths = sorted(list(val_images_dir.glob("*.png")))
    print(f"Total held-out validation images: {len(val_image_paths)}")

    onnx_path = PROJECT_ROOT / "ml" / "models" / "checkpoints" / "dentex_fdi_yolov8n_best.onnx"
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    inp_name = sess.get_inputs()[0].name

    solver = CalibratedFDISolver(enable_abstention=False)

    iou_thresh_list = [0.3, 0.4, 0.5]
    results = {
        thresh: {
            "gt_total": 0,
            "detected": 0,
            "correct_a": 0,
            "correct_b": 0,
        }
        for thresh in iou_thresh_list
    }

    quad_total = defaultdict(int)
    quad_correct_a = defaultdict(int)
    pos_total = defaultdict(int)
    pos_correct_a = defaultdict(int)

    t0 = time.perf_counter()

    for img_p in val_image_paths:
        label_p = val_labels_dir / f"{img_p.stem}.txt"
        if not label_p.exists():
            continue

        with Image.open(img_p) as pil_img:
            orig_w, orig_h = pil_img.size
            img = pil_img.convert("RGB")

        # Read ground truth
        gt_teeth = []
        with open(label_p, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                cls_id = int(parts[0])
                cx = float(parts[1]) * orig_w
                cy = float(parts[2]) * orig_h
                bw = float(parts[3]) * orig_w
                bh = float(parts[4]) * orig_h
                x1 = cx - bw / 2.0
                y1 = cy - bh / 2.0
                x2 = cx + bw / 2.0
                y2 = cy + bh / 2.0
                fdi = class_idx_to_fdi(cls_id)
                q = fdi // 10
                p = fdi % 10
                gt_teeth.append({
                    "bbox": [x1, y1, x2, y2],
                    "fdi": fdi,
                    "quadrant": q,
                    "position": p,
                })

        # Run ONNX inference
        tensor, meta = ImagePreprocessor.letterbox(img, target_size=640)
        outputs = sess.run(None, {inp_name: tensor})
        pred = outputs[0][0] # shape (36, 8400)
        # Transpose to (8400, 36)
        pred = np.transpose(pred, (1, 0))

        boxes_xywh = pred[:, :4]
        class_scores = pred[:, 4:] # 32 classes

        max_scores = np.max(class_scores, axis=1)
        argmax_classes = np.argmax(class_scores, axis=1)

        # Filter confidence >= 0.25
        cand_idx = np.where(max_scores >= 0.25)[0]
        # Sort by confidence descending
        cand_idx = cand_idx[np.argsort(-max_scores[cand_idx])]

        # NMS
        kept_proposals = []
        seen_boxes = []
        for ci in cand_idx:
            sc = float(max_scores[ci])
            cls_i = int(argmax_classes[ci])
            cx, cy, w, h = boxes_xywh[ci]

            x1_lb = cx - w / 2.0
            y1_lb = cy - h / 2.0
            x2_lb = cx + w / 2.0
            y2_lb = cy + h / 2.0

            box_orig = ImagePreprocessor.unletterbox_box([x1_lb, y1_lb, x2_lb, y2_lb], meta)

            dup = False
            for sb in seen_boxes:
                if compute_box_iou(box_orig, sb) > 0.45:
                    dup = True
                    break
            if dup:
                continue

            seen_boxes.append(box_orig)
            fdi_pred = class_idx_to_fdi(cls_i)
            kept_proposals.append({
                "bbox": box_orig,
                "confidence": sc,
                "predicted_fdi": fdi_pred,
                "class_idx": cls_i,
            })

        # Run Strategy B (CalibratedFDISolver)
        solver_proposals = [
            {"bbox": p["bbox"], "confidence": p["confidence"], "class_idx": p["class_idx"]}
            for p in kept_proposals
        ]
        try:
            solved_b = solver.solve(solver_proposals, image_width=orig_w, image_height=orig_h)
        except Exception as e:
            print(f"Solver B error: {e}")
            solved_b = []

        b_map = {}
        for sp in solved_b:
            key = (round(sp.bbox[0], 1), round(sp.bbox[1], 1))
            b_map[key] = sp.fdi_number

        # Evaluate against GT for each IoU threshold
        for thresh in iou_thresh_list:
            gt_matched = [False] * len(gt_teeth)
            results[thresh]["gt_total"] += len(gt_teeth)

            # Match proposals to GT greedily by IoU
            for prop in kept_proposals:
                best_iou = 0.0
                best_gt_idx = -1
                for gi, gt in enumerate(gt_teeth):
                    if gt_matched[gi]:
                        continue
                    iou = compute_box_iou(prop["bbox"], gt["bbox"])
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = gi

                if best_iou >= thresh and best_gt_idx >= 0:
                    gt_matched[best_gt_idx] = True
                    results[thresh]["detected"] += 1
                    gt = gt_teeth[best_gt_idx]

                    # Strategy A
                    if prop["predicted_fdi"] == gt["fdi"]:
                        results[thresh]["correct_a"] += 1
                        if thresh == 0.4:
                            quad_correct_a[gt["quadrant"]] += 1
                            pos_correct_a[gt["position"]] += 1

                    # Strategy B
                    key = (round(prop["bbox"][0], 1), round(prop["bbox"][1], 1))
                    fdi_b = b_map.get(key)
                    if fdi_b == gt["fdi"]:
                        results[thresh]["correct_b"] += 1

                    if thresh == 0.4:
                        quad_total[gt["quadrant"]] += 1
                        pos_total[gt["position"]] += 1

    elapsed = time.perf_counter() - t0
    print(f"Evaluated {len(val_image_paths)} images in {elapsed:.2f}s ({elapsed/len(val_image_paths)*1000:.1f} ms/img)")

    out_metrics = {}
    for thresh in iou_thresh_list:
        r = results[thresh]
        rec = (r["detected"] / r["gt_total"] * 100) if r["gt_total"] else 0
        acc_a_matched = (r["correct_a"] / r["detected"] * 100) if r["detected"] else 0
        e2e_a = (r["correct_a"] / r["gt_total"] * 100) if r["gt_total"] else 0
        acc_b_matched = (r["correct_b"] / r["detected"] * 100) if r["detected"] else 0
        e2e_b = (r["correct_b"] / r["gt_total"] * 100) if r["gt_total"] else 0

        print(f"\n--- Results at IoU >= {thresh} ---")
        print(f"Total Ground Truth Teeth: {r['gt_total']}")
        print(f"Detection Recall:        {rec:.2f}% ({r['detected']}/{r['gt_total']})")
        print(f"Strategy (a) [Detector predicted class]:")
        print(f"  Exact FDI on matched:  {acc_a_matched:.2f}% ({r['correct_a']}/{r['detected']})")
        print(f"  End-to-End Exact FDI:  {e2e_a:.2f}% ({r['correct_a']}/{r['gt_total']})")
        print(f"Strategy (b) [CalibratedFDISolver ordering]:")
        print(f"  Exact FDI on matched:  {acc_b_matched:.2f}% ({r['correct_b']}/{r['detected']})")
        print(f"  End-to-End Exact FDI:  {e2e_b:.2f}% ({r['correct_b']}/{r['gt_total']})")

        out_metrics[f"iou_{thresh}"] = {
            "detection_recall_pct": round(rec, 2),
            "strat_a_matched_acc_pct": round(acc_a_matched, 2),
            "strat_a_e2e_acc_pct": round(e2e_a, 2),
            "strat_b_matched_acc_pct": round(acc_b_matched, 2),
            "strat_b_e2e_acc_pct": round(e2e_b, 2),
        }

    print("\n--- Strategy (a) Quadrant & Position Breakdown (IoU >= 0.4) ---")
    for q in sorted(quad_total.keys()):
        tot = quad_total[q]
        cor = quad_correct_a[q]
        pct = (cor / tot * 100) if tot else 0
        print(f"Quadrant {q}: {pct:.1f}% ({cor}/{tot})")

    print("\nPositions failing most:")
    pos_rates = []
    for p in sorted(pos_total.keys()):
        tot = pos_total[p]
        cor = pos_correct_a[p]
        pct = (cor / tot * 100) if tot else 0
        pos_rates.append((p, pct, cor, tot))
    pos_rates.sort(key=lambda x: x[1])
    for p, pct, cor, tot in pos_rates:
        print(f"Position {p}: {pct:.1f}% ({cor}/{tot})")

    with open(PROJECT_ROOT / "scratch" / "task_a_yolov8n_fdi_eval_results.json", "w", encoding="utf-8") as f:
        json.dump(out_metrics, f, indent=2)

if __name__ == "__main__":
    evaluate_yolov8n_fdi()
