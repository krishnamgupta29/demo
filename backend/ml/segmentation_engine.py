"""
Instance Segmentation Inference Engine for Dental Panoramic Radiographs.

Supports:
- Pretrained dental instance segmentation models (e.g. nsitnov/8024-yolov8-model)
- Fine-tuned 4-class DENTEX YOLOv8-seg models
- Extraction of genuine polygon masks (unletterboxed to original image coordinates)
- Strict clinical truthfulness: never invents masks for detection-only models
"""

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import time
from typing import Any, Optional
import numpy as np
from PIL import Image

from backend.config import settings
from backend.schemas.provenance import ModelAvailabilityStatus, ModelProvenance, PredictionSource
from .preprocessor import ImagePreprocessor, LetterboxMetadata


@dataclass
class InstanceSegmentationResult:
    """Detection and genuine instance segmentation mask in original image coordinates."""
    class_id: int
    class_name: str
    confidence: float
    bbox_orig: list[float]  # [x1, y1, x2, y2] in original image pixels
    mask_polygon: Optional[list[list[float]]] = None  # [[x, y], ...] in original image pixels
    has_mask: bool = False
    area_px: Optional[float] = None


class DentalSegmentationEngine:
    """Inference engine for dental instance segmentation models."""

    def __init__(
        self,
        model_id: str = "nsitnov-8024-seg",
        model_name: str = "Dental Restorations & Lesions Segmenter",
        version: str = "1.0.0",
        checkpoint_rel_path: str = "models/checkpoints/8024.pt",
        class_names: Optional[list[str]] = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.40,
    ):
        self.model_id = model_id
        self.model_name = model_name
        self.version = version
        self.checkpoint_rel_path = checkpoint_rel_path
        self.class_names = class_names or [
            "Caries",
            "Crown",
            "Filling",
            "Implant",
            "Missing-tooth-between",
            "Periapical-lesion",
            "Root Piece",
            "Root-Canal-Treatment",
        ]
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

        self._yolo_model: Any = None
        self._weights_hash: Optional[str] = None
        self._device: str = "cpu"

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

    def load_model(self) -> bool:
        if not self.is_available():
            self._yolo_model = None
            return False

        try:
            import os
            os.environ["YOLO_AUTOINSTALL"] = "0"
            from ultralytics import YOLO
            import torch

            if str(self.checkpoint_path).endswith(".onnx"):
                device = "cpu"
                self._yolo_model = YOLO(str(self.checkpoint_path), task="segment")
            else:
                device = "cuda:0" if torch.cuda.is_available() else "cpu"
                self._yolo_model = YOLO(str(self.checkpoint_path))
            self._device = device
            return True
        except ImportError:
            print("[DentalSegmentationEngine] ultralytics or torch not installed.")
            self._yolo_model = None
            return False
        except Exception as exc:
            print(f"[DentalSegmentationEngine] Error loading weights: {exc}")
            self._yolo_model = None
            return False

    def predict_image(
        self,
        image: Image.Image,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Execute instance segmentation on PIL Image.

        Extracts both bounding boxes and genuine polygon masks scaled back to original image space.
        """
        if not self.is_available():
            return {
                "status": ModelAvailabilityStatus.MODEL_UNAVAILABLE.value,
                "error": f"Segmentation checkpoint missing at {self.checkpoint_rel_path}",
                "findings": [],
                "latency_ms": None,
                "provenance": self.get_provenance().model_dump(),
            }

        if self._yolo_model is None:
            if not self.load_model():
                return {
                    "status": ModelAvailabilityStatus.ERROR.value,
                    "error": "Failed to initialize segmentation model engine (ultralytics/torch required)",
                    "findings": [],
                    "latency_ms": None,
                    "provenance": self.get_provenance().model_dump(),
                }

        conf_th = conf_threshold if conf_threshold is not None else self.conf_threshold
        iou_th = iou_threshold if iou_threshold is not None else self.iou_threshold

        try:
            orig_w, orig_h = image.size
            t0 = time.perf_counter()

            # Run Ultralytics YOLOv8 segmentation forward pass
            results = self._yolo_model.predict(
                source=image,
                conf=conf_th,
                iou=iou_th,
                device=self._device,
                verbose=False,
            )
            t1 = time.perf_counter()
            latency_ms = round((t1 - t0) * 1000.0, 2)

            detections: list[InstanceSegmentationResult] = []

            if results and len(results) > 0:
                res = results[0]
                boxes = res.boxes
                masks = res.masks

                has_masks = masks is not None and len(masks) > 0

                for i in range(len(boxes)):
                    box_xyxy = boxes.xyxy[i].cpu().numpy().tolist()
                    conf = float(boxes.conf[i].cpu().numpy())
                    cls_id = int(boxes.cls[i].cpu().numpy())
                    cls_name = self.class_names[cls_id] if cls_id < len(self.class_names) else f"class_{cls_id}"

                    poly_coords = None
                    area_px = None
                    if has_masks and i < len(masks.xy):
                        poly_pts = masks.xy[i]  # shape (N, 2) in original image pixel coords
                        if len(poly_pts) >= 3:
                            poly_coords = [[round(float(p[0]), 1), round(float(p[1]), 1)] for p in poly_pts]
                            # Polygon area using Shoelace formula
                            x = poly_pts[:, 0]
                            y = poly_pts[:, 1]
                            area_px = round(0.5 * float(np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))), 1)

                    detections.append(
                        InstanceSegmentationResult(
                            class_id=cls_id,
                            class_name=cls_name,
                            confidence=round(conf, 4),
                            bbox_orig=[round(c, 1) for c in box_xyxy],
                            mask_polygon=poly_coords,
                            has_mask=poly_coords is not None,
                            area_px=area_px,
                        )
                    )

            return {
                "status": ModelAvailabilityStatus.AVAILABLE.value,
                "findings": detections,
                "total_findings": len(detections),
                "latency_ms": latency_ms,
                "execution_provider": f"PyTorch_{self._device.upper()}",
                "provenance": self.get_provenance().model_dump(),
            }

        except Exception as exc:
            return {
                "status": ModelAvailabilityStatus.ERROR.value,
                "error": f"Segmentation forward pass failed: {str(exc)}",
                "findings": [],
                "latency_ms": None,
                "provenance": self.get_provenance().model_dump(),
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
            execution_provider=f"PyTorch_{self._device.upper()}",
            source_type=PredictionSource.AI_MODEL,
        )
