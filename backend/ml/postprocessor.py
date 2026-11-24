"""Postprocessing routines for object detection: tensor decoding, class-aware NMS, and coordinate mapping."""

from dataclasses import dataclass
from typing import Sequence, Optional
import numpy as np
from .preprocessor import ImagePreprocessor, LetterboxMetadata


@dataclass
class DetectionResult:
    """Individual detected anomaly output with truthful geometry attributes."""

    class_id: int
    class_name: str
    confidence: float
    bbox_orig: list[float]  # [x_min, y_min, x_max, y_max] in original image pixels
    geometry_type: str = "bbox"  # Strictly "bbox" for object detector outputs (no false polygon masks)
    has_mask: bool = False
    mask_polygon: Optional[list[list[float]]] = None



def nms_boxes(boxes_xyxy: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.35) -> list[int]:
    """Perform standard greedy Non-Maximum Suppression on bounding boxes.

    Args:
        boxes_xyxy: ndarray of shape (N, 4) in format [x1, y1, x2, y2].
        scores: ndarray of shape (N,) containing confidence scores.
        iou_threshold: Intersection over Union cutoff threshold.

    Returns:
        List of integer indices to keep, sorted by descending score.
    """
    if len(boxes_xyxy) == 0:
        return []

    x1 = boxes_xyxy[:, 0]
    y1 = boxes_xyxy[:, 1]
    x2 = boxes_xyxy[:, 2]
    y2 = boxes_xyxy[:, 3]

    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        if order.size == 1:
            break

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h

        union = areas[i] + areas[order[1:]] - inter
        iou = np.where(union > 0, inter / union, 0.0)

        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]

    return keep


def decode_yolo_detections(
    raw_output: np.ndarray,
    meta: LetterboxMetadata,
    class_names: Sequence[str],
    conf_threshold: float = 0.25,
    iou_threshold: float = 0.35,
) -> list[DetectionResult]:
    """Decode raw YOLO output tensor (shape [1, 4+num_classes, num_proposals]) into filtered detections.

    Args:
        raw_output: Raw output tensor from ONNX session (e.g. [1, 7, 8400]).
        meta: Letterbox transformation parameters.
        class_names: List of class labels corresponding to class score indices.
        conf_threshold: Minimum confidence score to retain a candidate box.
        iou_threshold: NMS overlap threshold.

    Returns:
        List of DetectionResult instances mapped to original image coordinates.
    """
    if raw_output.ndim == 3:
        raw_output = raw_output[0]  # shape (4 + num_classes, num_proposals)

    # Transpose to (num_proposals, 4 + num_classes)
    proposals = np.transpose(raw_output, (1, 0))
    boxes_cxcywh = proposals[:, :4]
    class_scores = proposals[:, 4:]

    num_classes = class_scores.shape[1]
    results: list[DetectionResult] = []

    # Perform class-aware NMS so different pathology classes do not suppress each other
    for cls_idx in range(num_classes):
        scores = class_scores[:, cls_idx]
        valid_mask = scores >= conf_threshold
        if not np.any(valid_mask):
            continue

        valid_boxes = boxes_cxcywh[valid_mask]
        valid_scores = scores[valid_mask]

        # Convert [cx, cy, w, h] in 640x640 space to [x1, y1, x2, y2]
        x1 = valid_boxes[:, 0] - valid_boxes[:, 2] / 2.0
        y1 = valid_boxes[:, 1] - valid_boxes[:, 3] / 2.0
        x2 = valid_boxes[:, 0] + valid_boxes[:, 2] / 2.0
        y2 = valid_boxes[:, 1] + valid_boxes[:, 3] / 2.0
        boxes_xyxy = np.column_stack([x1, y1, x2, y2])

        keep_indices = nms_boxes(boxes_xyxy, valid_scores, iou_threshold=iou_threshold)

        cls_name = class_names[cls_idx] if cls_idx < len(class_names) else f"class_{cls_idx}"
        for idx in keep_indices:
            box_lb = boxes_xyxy[idx]
            box_orig = ImagePreprocessor.unletterbox_box(box_lb, meta)

            # Reject degenerate or zero-area boxes
            if box_orig[2] <= box_orig[0] or box_orig[3] <= box_orig[1]:
                continue

            results.append(
                DetectionResult(
                    class_id=cls_idx,
                    class_name=cls_name,
                    confidence=round(float(valid_scores[idx]), 4),
                    bbox_orig=box_orig,
                    geometry_type="bbox",
                )
            )

    # Sort final detections by descending confidence
    results.sort(key=lambda d: d.confidence, reverse=True)
    return results
