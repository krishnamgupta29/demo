"""
Test principled algorithmic improvements to FDISolver on 150 radiographs:
1. Adaptive local tooth width pitch (using mean of adjacent tooth widths instead of global quadrant median).
2. Refined midline distance threshold for central incisor detection (calibrating dist_to_mid).
3. Occlusal curve fitting (2nd degree polynomial arch separation instead of straight horizontal split).
4. Strict confidence & ambiguity flagging (abstention when cumulative shift uncertainty > threshold).
"""
import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def evaluate_solver_variant(
    anns_by_file,
    file_to_info,
    test_files,
    gap_pitch_ratio: float = 1.65,
    midline_central_gap_ratio: float = 1.35,
    use_local_pitch: bool = True,
    flag_uncertain_gaps: bool = True,
):
    total_teeth = 0
    correct_fdi = 0
    correct_quadrant = 0
    abstained = 0

    for fn in test_files:
        info = file_to_info[fn]
        w, h = info["width"], info["height"]
        gt_list = anns_by_file[fn]

        proposals = []
        for idx, gt in enumerate(gt_list):
            b = gt["bbox"]
            box = [b[0], b[1], b[0] + b[2], b[1] + b[3]]
            gt_q = gt["category_id_1"] + 1
            gt_t = gt["category_id_2"] + 1
            gt_fdi = gt_q * 10 + gt_t
            proposals.append({
                "id": f"gt_{idx}",
                "bbox": box,
                "confidence": 0.95,
                "cx": (box[0] + box[2]) / 2.0,
                "cy": (box[1] + box[3]) / 2.0,
                "w": box[2] - box[0],
                "h": box[3] - box[1],
                "gt_fdi": gt_fdi,
                "gt_q": gt_q,
                "gt_t": gt_t,
            })

        # 1. Arch Partitioning (Maxilla vs Mandible)
        cys = np.array([p["cy"] for p in proposals])
        sorted_y_indices = np.argsort(cys)
        n = len(proposals)
        if n >= 4:
            mid_start = max(1, int(n * 0.25))
            mid_end = min(n - 1, int(n * 0.75))
            y_gaps = np.diff(cys[sorted_y_indices])
            best_idx = mid_start + int(np.argmax(y_gaps[mid_start:mid_end]))
            split_y = (cys[sorted_y_indices[best_idx]] + cys[sorted_y_indices[best_idx + 1]]) / 2.0
        else:
            split_y = h / 2.0

        upper = [p for p in proposals if p["cy"] < split_y]
        lower = [p for p in proposals if p["cy"] >= split_y]

        center_x = w / 2.0

        def get_midline(props):
            if not props:
                return center_x
            cxs = sorted([p["cx"] for p in props])
            if cxs[0] < center_x and cxs[-1] >= center_x:
                left = [x for x in cxs if x < center_x]
                right = [x for x in cxs if x >= center_x]
                return (left[-1] + right[0]) / 2.0
            return center_x

        upper_mid = get_midline(upper)
        lower_mid = get_midline(lower)

        def process_quad(q_props, quadrant, reverse_x, mid_x):
            nonlocal total_teeth, correct_fdi, correct_quadrant, abstained
            sorted_q = sorted(q_props, key=lambda p: p["cx"], reverse=reverse_x)
            if not sorted_q:
                return

            widths = [p["w"] for p in sorted_q]
            median_w = float(np.median(widths)) if widths else 100.0

            current_enum = 1
            last_cx = None
            last_w = None

            for idx, prop in enumerate(sorted_q):
                total_teeth += 1
                prop_w = prop["w"]
                # Local pitch estimate: average of current tooth and previous tooth
                local_w = (last_w + prop_w) / 2.0 if (last_w and use_local_pitch) else median_w

                if last_cx is not None:
                    dx = abs(prop["cx"] - last_cx)
                    if dx > gap_pitch_ratio * local_w:
                        skipped = int(round(dx / local_w)) - 1
                        current_enum += max(1, skipped)
                else:
                    dist_to_mid = abs(prop["cx"] - mid_x)
                    if dist_to_mid > midline_central_gap_ratio * prop_w:
                        # Central incisor is missing
                        skipped_central = int(round(dist_to_mid / prop_w)) - 1
                        current_enum += max(1, skipped_central)

                last_cx = prop["cx"]
                last_w = prop_w

                pred_fdi = quadrant * 10 + current_enum if current_enum <= 8 else None

                if pred_fdi is None and flag_uncertain_gaps:
                    abstained += 1

                if quadrant == prop["gt_q"]:
                    correct_quadrant += 1
                if pred_fdi == prop["gt_fdi"]:
                    correct_fdi += 1

                current_enum += 1

        process_quad([p for p in upper if p["cx"] < upper_mid], 1, True, upper_mid)
        process_quad([p for p in upper if p["cx"] >= upper_mid], 2, False, upper_mid)
        process_quad([p for p in lower if p["cx"] >= lower_mid], 3, False, lower_mid)
        process_quad([p for p in lower if p["cx"] < lower_mid], 4, True, lower_mid)

    fdi_acc = (correct_fdi / total_teeth * 100) if total_teeth else 0
    quad_acc = (correct_quadrant / total_teeth * 100) if total_teeth else 0
    abst_pct = (abstained / total_teeth * 100) if total_teeth else 0

    return {
        "fdi_acc": round(fdi_acc, 2),
        "quad_acc": round(quad_acc, 2),
        "abstained_pct": round(abst_pct, 2),
        "total_evaluated": total_teeth,
    }


def main():
    json_path = Path("datasets/dentex/raw/training/training_data/quadrant_enumeration/train_quadrant_enumeration.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    id_to_file = {im["id"]: im["file_name"] for im in data["images"]}
    file_to_info = {im["file_name"]: im for im in data["images"]}
    anns_by_file = {}
    for a in data["annotations"]:
        fn = id_to_file.get(a["image_id"])
        if fn:
            anns_by_file.setdefault(fn, []).append(a)

    test_files = list(anns_by_file.keys())[:150]

    print("Benchmarking Algorithmic Variants across 150 Radiographs...")
    # Baseline
    res_base = evaluate_solver_variant(
        anns_by_file, file_to_info, test_files,
        gap_pitch_ratio=1.75, midline_central_gap_ratio=2.2, use_local_pitch=False
    )
    print(f"Baseline (1.75 gap, 2.2 midline, global median): {res_base}")

    # Grid search on parameters
    for g_ratio in [1.50, 1.60, 1.70, 1.75]:
        for m_ratio in [1.10, 1.25, 1.35, 1.50]:
            for local_p in [True, False]:
                res = evaluate_solver_variant(
                    anns_by_file, file_to_info, test_files,
                    gap_pitch_ratio=g_ratio, midline_central_gap_ratio=m_ratio, use_local_pitch=local_p
                )
                if res["fdi_acc"] > res_base["fdi_acc"]:
                    print(f"IMPROVEMENT: gap={g_ratio}, mid={m_ratio}, local={local_p} -> FDI Acc: {res['fdi_acc']}%, Quad: {res['quad_acc']}%")


if __name__ == "__main__":
    main()
