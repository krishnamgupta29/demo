"""Run baseline evaluation of verified pretrained model on DENTEX dev evaluation split."""

import json
from pathlib import Path
import csv
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ml.dataset_utils import DENTEXDatasetReader
from backend.ml.evaluator import BaselineEvaluator


def main():
    print("=" * 70)
    print("DENTRACE LEVEL 2: REAL PRETRAINED MODEL BASELINE EVALUATION")
    print("=" * 70)

    # 1. Load dataset
    print("[1/4] Ingesting DENTEX annotations...")
    reader = DENTEXDatasetReader()
    images = reader.load()
    print(f"  Loaded {len(images)} images.")

    # 2. Imbalance report
    imbalance = reader.get_class_imbalance_report()
    print("\n[2/4] Class distribution:")
    for k, v in imbalance["class_counts_3_class"].items():
        pct = imbalance["class_percentages"][k]
        print(f"  - {k}: {v} ({pct}%)")
    print(f"  Unsupported in DENTEX: {imbalance['unsupported_in_dentex']}")

    # 3. Create reproducible dev split
    print("\n[3/4] Creating reproducible dev evaluation split (80/20, seed=42)...")
    train_ids, eval_ids = reader.create_reproducible_split(eval_ratio=0.20, random_seed=42)
    print(f"  Train split: {len(train_ids)} images")
    print(f"  Dev Eval split: {len(eval_ids)} images")

    eval_image_infos = [images[img_id] for img_id in eval_ids if img_id in images]

    # 4. Run baseline evaluation
    print(f"\n[4/4] Executing real ONNX inference across {len(eval_image_infos)} dev images...")
    evaluator = BaselineEvaluator(conf_threshold=0.25, iou_threshold=0.35)
    metrics = evaluator.evaluate_split(eval_image_infos)

    print("\n" + "=" * 70)
    print("BASELINE EVALUATION RESULTS (EXPLORATORY DEV SPLIT)")
    print("=" * 70)
    print(f"Total Images Evaluated: {metrics.total_images_evaluated}")
    print(f"mAP@50:    {metrics.map50:.4f}")
    print(f"mAP@50-95: {metrics.map50_95:.4f}")
    print("\nPer-Class Breakdown:")
    for cls_name, res in metrics.per_class_results.items():
        if isinstance(res, dict):
            print(f"  [{cls_name.upper()}]")
            print(f"    GT: {res['ground_truth_count']}, Preds: {res['prediction_count']}")
            print(f"    TP: {res['true_positives']}, FP: {res['false_positives']}, FN: {res['false_negatives']}")
            print(f"    Precision: {res['precision']:.4f}, Recall: {res['recall']:.4f}, F1: {res['f1']:.4f}")
            print(f"    AP50: {res['ap50']:.4f}, AP50-95: {res['ap50_95']:.4f}")
        else:
            print(f"  [{cls_name.upper()}]: {res}")

    print("\nCPU Latency Profile:")
    for k, v in metrics.cpu_latency_stats_ms.items():
        print(f"  {k}: {v} ms")
    print(f"Peak RAM Trace: {metrics.memory_footprint_mb} MB")

    # Save structured results
    out_dir = Path("docs")
    out_dir.mkdir(exist_ok=True)
    json_path = out_dir / "level_2_baseline_benchmark.json"

    export_data = {
        "benchmark_metadata": {
            "model_id": evaluator.engine.model_id,
            "model_name": evaluator.engine.model_name,
            "version": evaluator.engine.version,
            "weights_hash_sha256": evaluator.engine.compute_sha256(),
            "execution_provider": "CPUExecutionProvider",
            "conf_threshold": evaluator.conf_threshold,
            "iou_threshold": evaluator.iou_threshold,
            "evaluation_date": "2026-10-19",
            "split_type": metrics.split_type,
            "total_images": metrics.total_images_evaluated,
            "provenance_disclaimer": metrics.provenance_disclaimer,
        },
        "metrics_summary": {
            "mAP50": metrics.map50,
            "mAP50_95": metrics.map50_95,
            "per_class": metrics.per_class_results,
        },
        "latency_profile_ms": metrics.cpu_latency_stats_ms,
        "peak_ram_mb": metrics.memory_footprint_mb,
        "class_imbalance": imbalance,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2)
    print(f"\nSaved JSON results to {json_path}")

    # Also export CSV
    csv_path = out_dir / "level_2_baseline_benchmark.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Class", "GroundTruth", "Predictions", "TP", "FP", "FN", "Precision", "Recall", "F1", "AP50", "AP50_95"])
        for cls_name, res in metrics.per_class_results.items():
            if isinstance(res, dict):
                writer.writerow([
                    cls_name,
                    res["ground_truth_count"],
                    res["prediction_count"],
                    res["true_positives"],
                    res["false_positives"],
                    res["false_negatives"],
                    res["precision"],
                    res["recall"],
                    res["f1"],
                    res["ap50"],
                    res["ap50_95"],
                ])
            else:
                writer.writerow([cls_name, "UNSUPPORTED", "-", "-", "-", "-", "-", "-", "-", "-", "-"])
    print(f"Saved CSV results to {csv_path}")

if __name__ == "__main__":
    main()
