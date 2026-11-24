"""
Detailed Failure Analysis of FDISolver on DENTEX train_quadrant_enumeration.json.

Analyzes errors by:
1. Jaw (Maxilla vs Mandible)
2. Quadrant (Q1, Q2, Q3, Q4)
3. Tooth Position within Quadrant (1 to 8)
4. Dentition completeness (32 teeth vs <32 teeth with missing slots)
5. Gap pitch threshold sensitivity
6. Comparison of raw model vs heuristic solver
"""
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.ml.fdi_solver import FDISolver


def analyze_fdi_failures(num_images: int = 150):
    json_path = Path("datasets/dentex/raw/training/training_data/quadrant_enumeration/train_quadrant_enumeration.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Index by image
    id_to_file = {im["id"]: im["file_name"] for im in data["images"]}
    file_to_info = {im["file_name"]: im for im in data["images"]}
    anns_by_file = {}
    for a in data["annotations"]:
        fn = id_to_file.get(a["image_id"])
        if fn:
            anns_by_file.setdefault(fn, []).append(a)

    solver = FDISolver(
        dedup_iou_threshold=0.35,
        min_confidence=0.30,
        uncertain_confidence_threshold=0.50,
        gap_pitch_ratio_threshold=1.75,
    )

    stats = {
        "total_teeth": 0,
        "quadrant_correct": 0,
        "exact_fdi_correct": 0,
        "by_jaw": {"maxilla": {"total": 0, "correct": 0}, "mandible": {"total": 0, "correct": 0}},
        "by_quadrant": {1: {"total": 0, "correct": 0}, 2: {"total": 0, "correct": 0}, 3: {"total": 0, "correct": 0}, 4: {"total": 0, "correct": 0}},
        "by_tooth_position": {pos: {"total": 0, "correct": 0} for pos in range(1, 9)},
        "by_image_tooth_count": defaultdict(lambda: {"total": 0, "correct": 0}),
        "error_types": Counter(),
        "shift_errors": Counter(),  # (pred_pos - gt_pos)
    }

    test_files = list(anns_by_file.keys())[:num_images]

    for fn in test_files:
        info = file_to_info[fn]
        w, h = info["width"], info["height"]
        gt_list = anns_by_file[fn]
        img_tooth_count = len(gt_list)

        raw_props = []
        for idx, gt in enumerate(gt_list):
            b = gt["bbox"]
            box = [b[0], b[1], b[0] + b[2], b[1] + b[3]]
            gt_q = gt["category_id_1"] + 1
            gt_t = gt["category_id_2"] + 1
            gt_fdi = gt_q * 10 + gt_t
            raw_props.append({
                "id": f"gt_{idx}",
                "bbox": box,
                "confidence": 0.95,
                "gt_fdi": gt_fdi,
                "gt_q": gt_q,
                "gt_t": gt_t,
                "jaw": "maxilla" if gt_q in (1, 2) else "mandible",
            })

        resolved = solver.solve(raw_props, image_width=w, image_height=h)

        # Match each resolved tooth to corresponding proposal by IoU
        for r_tooth in resolved:
            # find matching proposal
            best_p = None
            best_iou = 0.0
            for p in raw_props:
                iou = solver._compute_iou(r_tooth.bbox, p["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_p = p

            if best_p and best_iou > 0.80:
                stats["total_teeth"] += 1
                gt_q = best_p["gt_q"]
                gt_t = best_p["gt_t"]
                gt_fdi = best_p["gt_fdi"]
                jaw = best_p["jaw"]

                # Jaw stats
                stats["by_jaw"][jaw]["total"] += 1
                stats["by_quadrant"][gt_q]["total"] += 1
                stats["by_tooth_position"][gt_t]["total"] += 1
                stats["by_image_tooth_count"][img_tooth_count]["total"] += 1

                # Check Quadrant
                if r_tooth.quadrant == gt_q:
                    stats["quadrant_correct"] += 1

                # Check Exact FDI
                if r_tooth.fdi_number == gt_fdi:
                    stats["exact_fdi_correct"] += 1
                    stats["by_jaw"][jaw]["correct"] += 1
                    stats["by_quadrant"][gt_q]["correct"] += 1
                    stats["by_tooth_position"][gt_t]["correct"] += 1
                    stats["by_image_tooth_count"][img_tooth_count]["correct"] += 1
                else:
                    if r_tooth.quadrant != gt_q:
                        stats["error_types"]["quadrant_partition_error"] += 1
                    else:
                        stats["error_types"]["intra_quadrant_enumeration_shift"] += 1
                        pred_pos = r_tooth.fdi_number % 10 if r_tooth.fdi_number else -1
                        shift = pred_pos - gt_t
                        stats["shift_errors"][shift] += 1

    total = stats["total_teeth"]
    quad_acc = (stats["quadrant_correct"] / total * 100) if total else 0
    fdi_acc = (stats["exact_fdi_correct"] / total * 100) if total else 0

    print("=" * 70)
    print("FDI SOLVER FAILURE ANALYSIS ON DENTEX")
    print("=" * 70)
    print(f"Total Teeth Evaluated: {total} across {len(test_files)} radiographs")
    print(f"Overall Quadrant Accuracy: {quad_acc:.2f}% ({stats['quadrant_correct']}/{total})")
    print(f"Overall Exact FDI Accuracy: {fdi_acc:.2f}% ({stats['exact_fdi_correct']}/{total})")

    print("\n--- By Jaw ---")
    for jaw, data in stats["by_jaw"].items():
        acc = (data["correct"] / data["total"] * 100) if data["total"] else 0
        print(f"  {jaw.capitalize()}: {acc:.2f}% ({data['correct']}/{data['total']})")

    print("\n--- By Quadrant ---")
    q_names = {1: "Q1 (Maxillary Right)", 2: "Q2 (Maxillary Left)", 3: "Q3 (Mandibular Left)", 4: "Q4 (Mandibular Right)"}
    for q, data in stats["by_quadrant"].items():
        acc = (data["correct"] / data["total"] * 100) if data["total"] else 0
        print(f"  {q_names[q]}: {acc:.2f}% ({data['correct']}/{data['total']})")

    print("\n--- By Tooth Position within Quadrant (1=Central Incisor, 8=Third Molar) ---")
    t_names = {1: "Central Incisor", 2: "Lateral Incisor", 3: "Canine", 4: "First Premolar", 5: "Second Premolar", 6: "First Molar", 7: "Second Molar", 8: "Third Molar"}
    for pos, data in stats["by_tooth_position"].items():
        acc = (data["correct"] / data["total"] * 100) if data["total"] else 0
        print(f"  Pos {pos} ({t_names[pos]}): {acc:.2f}% ({data['correct']}/{data['total']})")

    print("\n--- Error Breakdown ---")
    for err, cnt in stats["error_types"].items():
        pct = cnt / (total - stats["exact_fdi_correct"]) * 100 if (total - stats["exact_fdi_correct"]) else 0
        print(f"  {err}: {cnt} ({pct:.2f}% of errors)")

    print("\n--- Intra-Quadrant Shift Errors (Pred Pos - GT Pos) ---")
    for shift, cnt in sorted(stats["shift_errors"].items()):
        print(f"  Shift {shift:+d} slot(s): {cnt} occurrences")

    print("\n--- Accuracy vs Total Tooth Count in Radiograph ---")
    for t_cnt in sorted(stats["by_image_tooth_count"].keys()):
        d = stats["by_image_tooth_count"][t_cnt]
        acc = (d["correct"] / d["total"] * 100) if d["total"] else 0
        print(f"  {t_cnt} teeth in OPG: {acc:.2f}% ({d['correct']}/{d['total']})")

    return stats


if __name__ == "__main__":
    analyze_fdi_failures(num_images=150)
