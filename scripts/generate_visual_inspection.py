"""Generate visual prediction inspections comparing ground truth and ONNX model detections."""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageDraw, ImageFont
from backend.ml.dataset_utils import DENTEXDatasetReader
from backend.ml.inference_engine import ONNXInferenceEngine
from backend.ml.evaluator import box_iou


def draw_box_with_label(
    draw: ImageDraw.ImageDraw,
    box: list[float],
    label: str,
    color: tuple[int, int, int],
    width: int = 4,
):
    """Draw rectangle and prominent label tag."""
    x1, y1, x2, y2 = box
    draw.rectangle([x1, y1, x2, y2], outline=color, width=width)
    
    # Text banner above or inside box
    label_y = max(0, y1 - 22)
    draw.rectangle([x1, label_y, x1 + len(label) * 9 + 10, label_y + 20], fill=color)
    draw.text((x1 + 4, label_y + 2), label, fill=(255, 255, 255))


def main():
    print("Generating visual error analysis inspection cases...")
    reader = DENTEXDatasetReader()
    images = reader.load()
    train_ids, eval_ids = reader.create_reproducible_split(eval_ratio=0.20, random_seed=42)

    engine = ONNXInferenceEngine(
        model_id="liodon-panoramic-screener",
        model_name="Liodon Panoramic Anomaly Screener",
        version="1.0.0",
        checkpoint_rel_path="models/checkpoints/best.onnx",
        class_names=["caries", "periapical_lesion", "impacted_tooth"],
        conf_threshold=0.25,
        iou_threshold=0.35,
    )

    out_dir = PROJECT_ROOT / "docs" / "visual_inspection"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Find representative cases in eval split:
    # 1. Image with periapical lesion
    # 2. Image with impacted tooth
    # 3. Image with caries
    # 4. Multi-pathology image
    selected_cases = []
    for img_id in eval_ids:
        info = images[img_id]
        cats = {a.pathology_class for a in info.annotations}
        if "periapical_lesion" in cats and len(selected_cases) < 1:
            selected_cases.append((info, "Case 1: Periapical Lesion with Apical Radiolucency"))
        elif "impacted_tooth" in cats and "caries" in cats and len(selected_cases) < 3:
            selected_cases.append((info, f"Case {len(selected_cases)+1}: Multi-Pathology (Impacted Tooth + Caries)"))
        elif len(selected_cases) < 4:
            selected_cases.append((info, f"Case {len(selected_cases)+1}: Caries Detection & Cervical Burnout Screening"))

        if len(selected_cases) >= 4:
            break

    case_reports = []

    for idx, (img_info, case_title) in enumerate(selected_cases):
        print(f"\nProcessing {case_title} ({img_info.file_name})...")
        orig_img = Image.open(img_info.file_path).convert("RGB")
        
        # Inference
        infer_res = engine.predict_image(orig_img, conf_threshold=0.25, iou_threshold=0.35)
        preds = infer_res.get("findings", [])

        # Annotated image canvas
        annotated = orig_img.copy()
        draw = ImageDraw.Draw(annotated)

        gt_boxes = img_info.annotations
        matched_gt = set()

        # Compare predictions to ground truth
        report_entries = []
        for p in preds:
            best_iou = 0.0
            best_gt = None
            for g_idx, g in enumerate(gt_boxes):
                if g.pathology_class == p.class_name and g_idx not in matched_gt:
                    iou = box_iou(p.bbox_orig, g.bbox_xyxy)
                    if iou > best_iou:
                        best_iou = iou
                        best_gt = g
                        best_gt_idx = g_idx

            if best_iou >= 0.50 and best_gt is not None:
                matched_gt.add(best_gt_idx)
                status = "TP (True Positive)"
                color = (0, 200, 100)  # Green for True Positive
                draw_box_with_label(
                    draw,
                    p.bbox_orig,
                    f"TP: {p.class_name.upper()} (conf={p.confidence:.2f}, IoU={best_iou:.2f})",
                    color,
                )
            else:
                status = "FP (False Positive)"
                color = (255, 60, 60)  # Red for False Positive / Over-detection
                draw_box_with_label(
                    draw,
                    p.bbox_orig,
                    f"FP: {p.class_name.upper()} (conf={p.confidence:.2f})",
                    color,
                )

            report_entries.append({
                "type": status,
                "class": p.class_name,
                "confidence": p.confidence,
                "bbox": p.bbox_orig,
                "iou_with_gt": round(best_iou, 3),
            })

        # Draw any missed ground truth (False Negatives)
        for g_idx, g in enumerate(gt_boxes):
            if g_idx not in matched_gt:
                draw_box_with_label(
                    draw,
                    g.bbox_xyxy,
                    f"FN: Missed {g.pathology_class.upper()}",
                    (255, 180, 0),  # Yellow/Orange for Missed Ground Truth
                    width=3,
                )
                report_entries.append({
                    "type": "FN (False Negative)",
                    "class": g.pathology_class,
                    "confidence": None,
                    "bbox": g.bbox_xyxy,
                    "iou_with_gt": 0.0,
                })

        # Save annotated image
        save_path = out_dir / f"case_{idx+1}_{img_info.image_id}.png"
        annotated.save(save_path)
        print(f"  Saved inspection visualization: {save_path.name}")

        case_reports.append({
            "case_id": f"CASE-{idx+1}",
            "title": case_title,
            "image_id": img_info.image_id,
            "file_name": img_info.file_name,
            "dimensions": f"{img_info.width}x{img_info.height}",
            "findings": report_entries,
            "visualization_file": save_path.name,
        })

    # Save summary report JSON
    with open(out_dir / "visual_inspection_report.json", "w", encoding="utf-8") as f:
        json.dump(case_reports, f, indent=2)

    print("\nVisual inspection generation complete!")


if __name__ == "__main__":
    main()
