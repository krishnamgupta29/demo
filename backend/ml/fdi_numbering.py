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
        checkpoint_rel_path: str = "models/checkpoints/dental_fdi.onnx",
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.40,
    ):
        self.model_id = "abychkov-fdi-detection"
        self.model_name = "Dental FDI 32-Tooth Detector"
        self.version = "1.0.0"
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
            tensor, meta = ImagePreprocessor.letterbox(image, target_size=640)

            t0 = time.perf_counter()
            input_name = self._session.get_inputs()[0].name
            outputs = self._session.run(None, {input_name: tensor})
            t1 = time.perf_counter()
            latency_ms = round((t1 - t0) * 1000.0, 2)

            # Output shape is (1, 300, 36)
            proposals = outputs[0][0]  # shape (300, 36)
            coords = proposals[:, :4]  # normalized cx, cy, w, h
            class_scores = proposals[:, 4:]  # 32 class scores

            max_scores = np.max(class_scores, axis=1)
            argmax_classes = np.argmax(class_scores, axis=1)

            # Filter proposals above threshold
            candidate_indices = np.where(max_scores >= conf_th)[0]

            # Midline and occlusal plane estimations in normalized coordinates
            # Midline is horizontally center (~0.5)
            # Occlusal plane is vertically center (~0.5)
            teeth_list: list[ToothLocalization] = []
            seen_boxes = []

            for idx in candidate_indices:
                score = float(max_scores[idx])
                cls_idx = int(argmax_classes[idx])
                cx, cy, w, h = coords[idx]

                # Convert normalized coordinates to 640x640 space
                x1_lb = (cx - w / 2.0) * meta.target_size
                y1_lb = (cy - h / 2.0) * meta.target_size
                x2_lb = (cx + w / 2.0) * meta.target_size
                y2_lb = (cy + h / 2.0) * meta.target_size

                box_orig = ImagePreprocessor.unletterbox_box([x1_lb, y1_lb, x2_lb, y2_lb], meta)

                # Deduplication check against already accepted tooth boxes
                is_duplicate = False
                for sb in seen_boxes:
                    # Quick IoU check
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

                # Patient-side anatomical orientation:
                # OPG convention: patient right is image left, patient left is image right
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

                # Bychkov checkpoint limitation check:
                # Because the author's proprietary anatomical consistency engine is closed-source,
                # raw logit mapping without topological graph resolution has ambiguous class boundaries.
                # Therefore, we flag uncertain tooth numbers truthfully.
                uncertain = score < 0.55

                teeth_list.append(
                    ToothLocalization(
                        fdi_number=None,  # Not forcing unvalidated FDI number onto ambiguous proposals
                        confidence=round(score, 4),
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
