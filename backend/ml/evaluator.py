"""Baseline evaluation engine for real pretrained dental models on DENTEX dev split."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import time
from typing import Any, Optional
import numpy as np
from PIL import Image

from backend.config import settings
from .inference_engine import ONNXInferenceEngine
from .dataset_utils import DENTEXDatasetReader, DatasetImageInfo


def box_iou(box1: list[float], box2: list[float]) -> float:
    """Calculate Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2]."""
    xx1 = max(box1[0], box2[0])
    yy1 = max(box1[1], box2[1])
    xx2 = min(box1[2], box2[2])
    yy2 = min(box1[3], box2[3])

    w = max(0.0, xx2 - xx1)
    h = max(0.0, yy2 - yy1)
    inter = w * h

    a1 = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
    a2 = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0


@dataclass
class EvaluationMetrics:
    total_images_evaluated: int
    split_type: str  # "exploratory_dev_evaluation"
    classes_evaluated: list[str]
    unsupported_classes: list[str]
    per_class_results: dict[str, Any]
    map50: float
    map50_95: float
    cpu_latency_stats_ms: dict[str, float]
    memory_footprint_mb: float
    provenance_disclaimer: str


class BaselineEvaluator:
    """Executes transparent baseline evaluation on DENTEX images without synthetic metrics."""

    def __init__(
        self,
        engine: Optional[ONNXInferenceEngine] = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.35,
    ):
        self.engine = engine or ONNXInferenceEngine(
            model_id="liodon-panoramic-screener",
            model_name="Liodon Panoramic Anomaly Screener",
            version="1.0.0",
            checkpoint_rel_path="models/checkpoints/best.onnx",
            class_names=["caries", "periapical_lesion", "impacted_tooth"],
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
        )
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

    def evaluate_split(
        self,
        image_infos: list[DatasetImageInfo],
        max_images: Optional[int] = None,
    ) -> EvaluationMetrics:
        """Run inference across images and calculate real precision, recall, AP50, and latency."""
        import tracemalloc

        tracemalloc.start()
        t_start_total = time.perf_counter()

        eval_set = image_infos[:max_images] if max_images else image_infos
        classes = ["caries", "periapical_lesion", "impacted_tooth"]

        # Track per-class predictions and ground truths
        # Format: predictions[cls] = list of (score, is_tp_50, is_tp_iou_list)
        cls_preds: dict[str, list[dict]] = {c: [] for c in classes}
        cls_gt_counts: dict[str, int] = {c: 0 for c in classes}
        latencies_ms: list[float] = []

        # Count total ground truths
        for img in eval_set:
            for gt in img.annotations:
                if gt.pathology_class in cls_gt_counts:
                    cls_gt_counts[gt.pathology_class] += 1

        # Run inference on each image
        for img_info in eval_set:
            if not img_info.file_path.exists():
                continue

            try:
                pil_img = Image.open(img_info.file_path).convert("RGB")
            except Exception:
                continue

            t0 = time.perf_counter()
            infer_out = self.engine.predict_image(
                pil_img,
                conf_threshold=self.conf_threshold,
                iou_threshold=self.iou_threshold,
            )
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

            if infer_out["status"].lower() != "available":
                continue

            preds = infer_out["findings"]

            # Match predictions against ground truth for this image
            # Separate by class
            for cls_name in classes:
                gt_boxes = [a.bbox_xyxy for a in img_info.annotations if a.pathology_class == cls_name]
                p_boxes = [p for p in preds if p.class_name == cls_name]

                # Sort predictions by confidence descending
                p_boxes.sort(key=lambda x: x.confidence, reverse=True)
                matched_gt_50 = set()

                for p in p_boxes:
                    best_iou = 0.0
                    best_gt_idx = -1
                    for idx, gtb in enumerate(gt_boxes):
                        if idx in matched_gt_50:
                            continue
                        iou = box_iou(p.bbox_orig, gtb)
                        if iou > best_iou:
                            best_iou = iou
                            best_gt_idx = idx

                    is_tp_50 = False
                    if best_iou >= 0.50 and best_gt_idx >= 0:
                        is_tp_50 = True
                        matched_gt_50.add(best_gt_idx)

                    # Calculate matches across IoU thresholds [0.50:0.95:0.05]
                    iou_thresholds = np.linspace(0.50, 0.95, 10)
                    is_tp_ious = [best_iou >= th for th in iou_thresholds]

                    cls_preds[cls_name].append({
                        "confidence": p.confidence,
                        "is_tp_50": is_tp_50,
                        "is_tp_ious": is_tp_ious,
                    })

        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_ram_mb = round(peak_bytes / (1024 * 1024), 2)

        # Calculate AP and mAP
        per_class_results = {}
        ap50_list = []
        ap50_95_list = []

        for cls_name in classes:
            preds_list = cls_preds[cls_name]
            n_gt = cls_gt_counts[cls_name]

            if len(preds_list) == 0:
                per_class_results[cls_name] = {
                    "ground_truth_count": n_gt,
                    "prediction_count": 0,
                    "true_positives": 0,
                    "false_positives": 0,
                    "false_negatives": n_gt,
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1": 0.0,
                    "ap50": 0.0,
                    "ap50_95": 0.0,
                }
                ap50_list.append(0.0)
                ap50_95_list.append(0.0)
                continue

            # Sort all predictions of this class across dataset by confidence descending
            preds_list.sort(key=lambda x: x["confidence"], reverse=True)

            tp_50 = np.array([x["is_tp_50"] for x in preds_list], dtype=float)
            fp_50 = 1.0 - tp_50

            acc_tp_50 = np.cumsum(tp_50)
            acc_fp_50 = np.cumsum(fp_50)

            rec_50 = acc_tp_50 / n_gt if n_gt > 0 else np.zeros_like(acc_tp_50)
            prec_50 = acc_tp_50 / (acc_tp_50 + acc_fp_50)

            # 11-point interpolated AP50
            ap50 = 0.0
            for r_th in np.linspace(0.0, 1.0, 11):
                p_interp = prec_50[rec_50 >= r_th]
                if len(p_interp) > 0:
                    ap50 += np.max(p_interp)
            ap50 /= 11.0

            # AP across IoU range [0.50..0.95]
            ap_ious = []
            for th_idx in range(10):
                tp_th = np.array([x["is_tp_ious"][th_idx] for x in preds_list], dtype=float)
                fp_th = 1.0 - tp_th
                acc_tp = np.cumsum(tp_th)
                acc_fp = np.cumsum(fp_th)
                rec = acc_tp / n_gt if n_gt > 0 else np.zeros_like(acc_tp)
                prec = acc_tp / (acc_tp + acc_fp)
                sub_ap = 0.0
                for r_th in np.linspace(0.0, 1.0, 11):
                    p_interp = prec[rec >= r_th]
                    if len(p_interp) > 0:
                        sub_ap += np.max(p_interp)
                ap_ious.append(sub_ap / 11.0)
            ap50_95 = float(np.mean(ap_ious))

            total_tp = int(np.sum(tp_50))
            total_fp = int(np.sum(fp_50))
            total_fn = max(0, n_gt - total_tp)
            final_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
            final_r = total_tp / n_gt if n_gt > 0 else 0.0
            f1 = (2 * final_p * final_r) / (final_p + final_r) if (final_p + final_r) > 0 else 0.0

            per_class_results[cls_name] = {
                "ground_truth_count": n_gt,
                "prediction_count": len(preds_list),
                "true_positives": total_tp,
                "false_positives": total_fp,
                "false_negatives": total_fn,
                "precision": round(float(final_p), 4),
                "recall": round(float(final_r), 4),
                "f1": round(float(f1), 4),
                "ap50": round(float(ap50), 4),
                "ap50_95": round(float(ap50_95), 4),
            }
            ap50_list.append(ap50)
            ap50_95_list.append(ap50_95)

        # Report unsupported classes explicitly
        for unsup in DENTEXDatasetReader.UNSUPPORTED_CLASSES:
            per_class_results[unsup] = "UNSUPPORTED"

        # Latency statistics
        lat_arr = np.array(latencies_ms) if len(latencies_ms) > 0 else np.array([0.0])
        lat_stats = {
            "mean_ms": round(float(np.mean(lat_arr)), 2),
            "median_p50_ms": round(float(np.median(lat_arr)), 2),
            "p95_ms": round(float(np.percentile(lat_arr, 95)), 2),
            "min_ms": round(float(np.min(lat_arr)), 2),
            "max_ms": round(float(np.max(lat_arr)), 2),
        }

        return EvaluationMetrics(
            total_images_evaluated=len(eval_set),
            split_type="exploratory_dev_evaluation",
            classes_evaluated=classes,
            unsupported_classes=DENTEXDatasetReader.UNSUPPORTED_CLASSES,
            per_class_results=per_class_results,
            map50=round(float(np.mean(ap50_list)), 4),
            map50_95=round(float(np.mean(ap50_95_list)), 4),
            cpu_latency_stats_ms=lat_stats,
            memory_footprint_mb=peak_ram_mb,
            provenance_disclaimer=(
                "EXPLORATORY EVALUATION NOTICE: The candidate model liodon-ai/dental-panoramic-detector was "
                "pretrained by its authors on combined DENTEX + OralXrays-9 data. Therefore, this benchmark "
                "serves as an exploratory reproducibility and sanity check baseline rather than a zero-shot "
                "independent clinical validation. Zero synthetic scores were generated."
            ),
        )
