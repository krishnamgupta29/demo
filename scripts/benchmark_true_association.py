"""
True Association & FDI Evaluation on the canonical 141-image validation split.

Separates:
1. Association Coverage: % of findings mapped to ANY tooth bounding box
2. Correct Tooth Association Rate: % of findings mapped to the correct ground-truth FDI
3. Wrong Tooth Association Rate: % of findings mapped to a wrong FDI number
4. Unassociated Rate: % of findings not mapped to any tooth
5. Independent Ground-Truth Association (when tooth identity is known)
6. Error attribution: Breakdown between geometric association error vs FDI numbering solver error
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from PIL import Image

from backend.ml.fdi_numbering import FDINumberingEngine
from backend.ml.fdi_solver import FDISolver
from backend.ml.association import ToothPathologyAssociator


def run_true_association_benchmark(num_images: int = 50):
    json_path = Path("datasets/dentex/raw/training/training_data/quadrant-enumeration-disease/train_quadrant_enumeration_disease.json")
    img_dir = Path("datasets/dentex/raw/training/training_data/quadrant-enumeration-disease/xrays")
    
    with open(json_path, "r", encoding="utf-8") as f:
        dis_data = json.load(f)

    # Reconstruct the exact 141-image validation partition (seed=42)
    images = {img["id"]: img for img in dis_data["images"]}
    sorted_ids = sorted(images.keys())
    rng = np.random.RandomState(42)
    shuffled = sorted_ids.copy()
    rng.shuffle(shuffled)
    n_val = int(round(len(shuffled) * 0.20))
    val_ids = set(shuffled[:n_val])

    anns_by_img = {}
    for a in dis_data["annotations"]:
        if a["image_id"] in val_ids:
            anns_by_img.setdefault(a["image_id"], []).append(a)

    print(f"Validation Partition: {len(val_ids)} images, {sum(len(v) for v in anns_by_img.values())} total annotations.")
    
    fdi_engine = FDINumberingEngine()
    fdi_engine.load_session()
    solver = FDISolver()
    associator = ToothPathologyAssociator()

    total_findings = 0
    associated_count = 0
    unassociated_count = 0
    correct_fdi_count = 0
    wrong_fdi_count = 0
    
    # Track why wrong:
    # A: Geometric match was to the correct physical tooth, but the tooth had a wrong FDI assigned by FDISolver
    # B: Geometric match selected the wrong physical tooth entirely
    geometric_correct_tooth_but_wrong_fdi = 0
    geometric_wrong_tooth = 0

    evaluated_images = list(val_ids)[:num_images]

    for img_id in evaluated_images:
        info = images[img_id]
        img_path = img_dir / info["file_name"]
        if not img_path.exists():
            continue
            
        pil_img = Image.open(img_path).convert("RGB")
        w, h = pil_img.size
        
        # 1. Run real RT-DETR tooth detection
        fdi_res = fdi_engine.predict_teeth(pil_img)
        raw_teeth = fdi_res.get("teeth", [])
        resolved_teeth = solver.solve(
            [{"id": f"tooth_{i}", "bbox": t.bbox_orig, "confidence": t.confidence} for i, t in enumerate(raw_teeth)],
            image_width=w,
            image_height=h,
        )

        # 2. Extract ground-truth findings from DENTEX
        gt_findings = []
        for idx, a in enumerate(anns_by_img.get(img_id, [])):
            b = a["bbox"]
            f_box = [b[0], b[1], b[0] + b[2], b[1] + b[3]]
            gt_fdi = (a["category_id_1"] + 1) * 10 + (a["category_id_2"] + 1)
            gt_findings.append({
                "id": f"finding_{idx}",
                "label": f"Disease_{a['category_id_3']}",
                "confidence": 1.0,
                "bbox": f_box,
                "gt_fdi": gt_fdi,
            })

        total_findings += len(gt_findings)
        teeth_with_finds, associations = associator.associate(gt_findings, resolved_teeth)

        for a, orig in zip(associations, gt_findings):
            if a.associated_fdi_number is not None:
                associated_count += 1
                if a.associated_fdi_number == orig["gt_fdi"]:
                    correct_fdi_count += 1
                else:
                    wrong_fdi_count += 1
                    # Check if the associated tooth box actually matches the GT finding box (IoU > 0.40)
                    # Find associated tooth
                    assoc_tooth = next((t for t in resolved_teeth if t.tooth_id == a.associated_tooth_id), None)
                    if assoc_tooth:
                        inter, a1, a2 = associator._box_intersection_and_areas(orig["bbox"], assoc_tooth.bbox)
                        union = a1 + a2 - inter
                        iou = inter / union if union > 0 else 0
                        iop = inter / a1 if a1 > 0 else 0
                        if iop >= 0.40 or iou >= 0.35:
                            # It physically hit the host tooth box, but the FDI label assigned by FDISolver was wrong
                            geometric_correct_tooth_but_wrong_fdi += 1
                        else:
                            geometric_wrong_tooth += 1
            else:
                unassociated_count += 1

    coverage_pct = (associated_count / total_findings * 100) if total_findings else 0
    correct_fdi_pct = (correct_fdi_count / total_findings * 100) if total_findings else 0
    wrong_fdi_pct = (wrong_fdi_count / total_findings * 100) if total_findings else 0
    unassoc_pct = (unassociated_count / total_findings * 100) if total_findings else 0

    results = {
        "num_images_evaluated": len(evaluated_images),
        "total_findings": total_findings,
        "association_coverage_pct": round(coverage_pct, 2),
        "correct_tooth_association_rate_pct": round(correct_fdi_pct, 2),
        "wrong_tooth_association_rate_pct": round(wrong_fdi_pct, 2),
        "unassociated_rate_pct": round(unassoc_pct, 2),
        "error_decomposition": {
            "geometric_hit_host_tooth_but_fdi_solver_numbered_wrong": geometric_correct_tooth_but_wrong_fdi,
            "geometric_matched_wrong_tooth_entirely": geometric_wrong_tooth,
            "unassociated_findings": unassociated_count,
        }
    }

    print("\n" + "=" * 70)
    print("TRUE ASSOCIATION EVALUATION RESULTS")
    print("=" * 70)
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    run_true_association_benchmark(num_images=50)
