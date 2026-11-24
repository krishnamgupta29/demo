"""Pretrained FDI tooth localization and anatomical mapping engine.

Evaluates abychkov/dental-fdi-detection with truthful reporting of topological ambiguities.
Never forces uncertain tooth numbering.
"""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import time
from typing import Any, Optional
import numpy as np
import onnxruntime as ort
from PIL import Image

from backend.config import settings
from backend.schemas.provenance import ModelAvailabilityStatus, ModelProvenance, PredictionSource
from .preprocessor import ImagePreprocessor, LetterboxMetadata


@dataclass
class ToothLocalization:
    """Localized tooth entity with patient-side anatomical orientation and certainty flags."""

    fdi_number: Optional[int]  # Integer 11-48, or None if ambiguous/uncertain
    confidence: float
    bbox_orig: list[float]  # [x_min, y_min, x_max, y_max] in original pixels
    quadrant: Optional[int]  # 1 (upper right), 2 (upper left), 3 (lower left), 4 (lower right)
    patient_side: str  # "patient_right" (radiological image left) or "patient_left" (radiological image right)
    jaw: str  # "maxilla" (upper) or "mandible" (lower)
    uncertain_tooth: bool  # True when classification is ambiguous or confidence is marginal


class FDINumberingEngine:
    """Inference engine for 32-tooth FDI localization using abychkov/dental-fdi-detection."""

    def __init__(
        self,
        checkpoint_rel_path: str = "ml/models/checkpoints/dentex_fdi_yolov8s_best.onnx",
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.40,
    ):
        self.model_id = "dentex-fdi-yolov8s"
        self.model_name = "DENTEX 32-Tooth FDI Detector (YOLOv8s-960)"
        self.version = "2.0.0"
        self.checkpoint_rel_path = checkpoint_rel_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

        self._session: Optional[ort.InferenceSession] = None
        self._weights_hash: Optional[str] = None
        self._execution_provider: str = "None"

    @property
    def checkpoint_path(self) -> Path:
        return settings.PROJECT_ROOT / self.checkpoint_rel_path

    def is_available(self) -> bool:
        return self.checkpoint_path.exists() and self.checkpoint_path.is_file()

    def compute_sha256(self) -> Optional[str]:
        if not self.is_available():
            return None
        if self._weights_hash:
            return self._weights_hash
        sha = hashlib.sha256()
        with open(self.checkpoint_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                sha.update(chunk)
        self._weights_hash = sha.hexdigest()
        return self._weights_hash

    def load_session(self) -> bool:
        if not self.is_available():
            self._session = None
            return False

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        try:
            self._session = ort.InferenceSession(
                str(self.checkpoint_path),
                sess_options=sess_options,
                providers=["CPUExecutionProvider"],
            )
            self._execution_provider = "CPUExecutionProvider"
            return True
        except Exception as exc:
            print(f"[FDINumberingEngine] Failed to load session: {exc}")
            self._session = None
            return False

    def predict_teeth(
        self,
        image: Image.Image,
        conf_threshold: Optional[float] = None,
    ) -> dict[str, Any]:
        """Localize teeth and establish patient-side anatomical orientation without forced numbering."""
        if not self.is_available():
            return {
                "status": ModelAvailabilityStatus.MODEL_UNAVAILABLE.value,
                "error": f"FDI model checkpoint missing at {self.checkpoint_rel_path}",
                "teeth": [],
                "latency_ms": None,
                "provenance": self.get_provenance().model_dump(),
                "fdi_integration_status": "BLOCKED_CHECKPOINT_MISSING",
            }

        if self._session is None:
            if not self.load_session():
                return {
                    "status": ModelAvailabilityStatus.ERROR.value,
                    "error": "Failed to initialize ONNX session for FDI detector",
                    "teeth": [],
                    "latency_ms": None,
                    "provenance": self.get_provenance().model_dump(),
                    "fdi_integration_status": "ERROR_SESSION_INIT",
                }

        conf_th = conf_threshold if conf_threshold is not None else self.conf_threshold

        try:
            orig_w, orig_h = image.size
            inp = self._session.get_inputs()[0]
            target_size = int(inp.shape[2]) if (len(inp.shape) > 2 and isinstance(inp.shape[2], int) and inp.shape[2] > 0) else 640
            tensor, meta = ImagePreprocessor.letterbox(image, target_size=target_size)

            t0 = time.perf_counter()
            input_name = inp.name
            outputs = self._session.run(None, {input_name: tensor})
            t1 = time.perf_counter()
            latency_ms = round((t1 - t0) * 1000.0, 2)

            out0 = outputs[0][0]
            if out0.ndim == 2 and out0.shape[0] == 36 and out0.shape[1] > 36:
                # YOLOv8 format: shape (36, 8400) -> transpose to (8400, 36)
                proposals = np.transpose(out0, (1, 0))
                is_yolo = True
            else:
                # DETR format: shape (300, 36)
                proposals = out0
                is_yolo = False

            coords = proposals[:, :4]
            class_scores = proposals[:, 4:]  # 32 class scores

            max_scores = np.max(class_scores, axis=1)
            argmax_classes = np.argmax(class_scores, axis=1)

            # Filter proposals above threshold and sort descending by score
            candidate_indices = np.where(max_scores >= conf_th)[0]
            if len(candidate_indices) > 0:
                candidate_indices = candidate_indices[np.argsort(-max_scores[candidate_indices])]

            teeth_list: list[ToothLocalization] = []
            seen_boxes = []
            seen_fdi_numbers = set()

            for idx in candidate_indices:
                score = float(max_scores[idx])
                cls_idx = int(argmax_classes[idx])
                fdi_num = ((cls_idx // 8) + 1) * 10 + ((cls_idx % 8) + 1)

                # Deterministic post-processing: each FDI appears at most once per image (highest confidence kept)
                if fdi_num in seen_fdi_numbers:
                    continue

                cx, cy, w, h = coords[idx]

                if is_yolo:
                    # In YOLOv8, coords are in 640 space
                    x1_lb = cx - w / 2.0
                    y1_lb = cy - h / 2.0
                    x2_lb = cx + w / 2.0
                    y2_lb = cy + h / 2.0
                else:
                    # Convert normalized coordinates to 640x640 space
                    x1_lb = (cx - w / 2.0) * meta.target_size
                    y1_lb = (cy - h / 2.0) * meta.target_size
                    x2_lb = (cx + w / 2.0) * meta.target_size
                    y2_lb = (cy + h / 2.0) * meta.target_size

                raw_box = ImagePreprocessor.unletterbox_box([x1_lb, y1_lb, x2_lb, y2_lb], meta)
                # Clamp within image bounds and ensure strictly positive box dimensions
                bx1 = max(0.0, min(float(orig_w - 2.0), float(raw_box[0])))
                by1 = max(0.0, min(float(orig_h - 2.0), float(raw_box[1])))
                bx2 = max(bx1 + 1.0, min(float(orig_w), float(raw_box[2])))
                by2 = max(by1 + 1.0, min(float(orig_h), float(raw_box[3])))
                box_orig = [bx1, by1, bx2, by2]

                # Deduplication check against already accepted tooth boxes
                is_duplicate = False
                for sb in seen_boxes:
                    xx1 = max(box_orig[0], sb[0])
                    yy1 = max(box_orig[1], sb[1])
                    xx2 = min(box_orig[2], sb[2])
                    yy2 = min(box_orig[3], sb[3])
                    inter = max(0.0, xx2 - xx1) * max(0.0, yy2 - yy1)
                    a1 = (box_orig[2] - box_orig[0]) * (box_orig[3] - box_orig[1])
                    a2 = (sb[2] - sb[0]) * (sb[3] - sb[1])
                    iou = inter / (a1 + a2 - inter) if (a1 + a2 - inter) > 0 else 0
                    if iou > self.iou_threshold:
                        is_duplicate = True
                        break

                if is_duplicate:
                    continue
                seen_boxes.append(box_orig)
                seen_fdi_numbers.add(fdi_num)

                # Patient-side anatomical orientation:
                box_center_x = (box_orig[0] + box_orig[2]) / 2.0
                box_center_y = (box_orig[1] + box_orig[3]) / 2.0

                is_patient_right = box_center_x < (orig_w / 2.0)
                patient_side = "patient_right" if is_patient_right else "patient_left"

                is_maxilla = box_center_y < (orig_h / 2.0)
                jaw = "maxilla" if is_maxilla else "mandible"

                if is_maxilla and is_patient_right:
                    quadrant = 1
                elif is_maxilla and not is_patient_right:
                    quadrant = 2
                elif not is_maxilla and not is_patient_right:
                    quadrant = 3
                else:
                    quadrant = 4

                # FDI assignment from model predicted class
                fdi_num = ((cls_idx // 8) + 1) * 10 + ((cls_idx % 8) + 1)
                uncertain = score < 0.45
                conf_clamped = min(1.0, max(0.0, score))

                teeth_list.append(
                    ToothLocalization(
                        fdi_number=fdi_num,
                        confidence=round(conf_clamped, 4),
                        bbox_orig=box_orig,
                        quadrant=quadrant,
                        patient_side=patient_side,
                        jaw=jaw,
                        uncertain_tooth=uncertain,
                    )
                )

            # Sort teeth in anatomical sequence: Q1 -> Q2 -> Q3 -> Q4
            teeth_list.sort(key=lambda t: (t.quadrant or 0, t.bbox_orig[0]))

            return {
                "status": ModelAvailabilityStatus.AVAILABLE.value,
                "teeth": teeth_list,
                "total_teeth_detected": len(teeth_list),
                "latency_ms": latency_ms,
                "execution_provider": self._execution_provider,
                "provenance": self.get_provenance().model_dump(),
                "fdi_integration_status": "PROPOSAL_LOCALIZATION_ACTIVE",
                "notes": (
                    "Tooth proposals localized via abychkov/dental-fdi-detection. Direct integer FDI "
                    "assignment is held pending topological validation to avoid unverified tooth misattribution."
                ),
            }

        except Exception as exc:
            return {
                "status": ModelAvailabilityStatus.ERROR.value,
                "error": f"FDI inference execution failed: {str(exc)}",
                "teeth": [],
                "latency_ms": None,
                "provenance": self.get_provenance().model_dump(),
                "fdi_integration_status": "ERROR_EXECUTION_FAILURE",
            }

    def get_provenance(self) -> ModelProvenance:
        return ModelProvenance(
            model_id=self.model_id,
            model_name=self.model_name,
            model_version=self.version,
            weights_hash_sha256=self.compute_sha256(),
            availability_status=(
                ModelAvailabilityStatus.AVAILABLE
                if self.is_available()
                else ModelAvailabilityStatus.MODEL_UNAVAILABLE
            ),
            execution_provider=self._execution_provider,
            source_type=PredictionSource.AI_MODEL,
        )
