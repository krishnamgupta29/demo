"""Real ONNX Runtime model inference engine with SHA-256 integrity checks, CPU fallback, and latency tracking."""

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
from .postprocessor import DetectionResult, decode_yolo_detections


class ONNXInferenceEngine:
    """Manages ONNX Runtime sessions, pre/postprocessing, and execution provenance."""

    def __init__(
        self,
        model_id: str,
        model_name: str,
        version: str,
        checkpoint_rel_path: str,
        class_names: list[str],
        input_size: int = 640,
        expected_sha256: Optional[str] = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.35,
    ):
        self.model_id = model_id
        self.model_name = model_name
        self.version = version
        self.checkpoint_rel_path = checkpoint_rel_path
        self.class_names = class_names
        self.input_size = input_size
        self.expected_sha256 = expected_sha256
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

        self._session: Optional[ort.InferenceSession] = None
        self._execution_provider: str = "None"
        self._weights_hash: Optional[str] = None

    @property
    def checkpoint_path(self) -> Path:
        return settings.PROJECT_ROOT / self.checkpoint_rel_path

    def is_available(self) -> bool:
        """Verify that the checkpoint file exists on disk."""
        return self.checkpoint_path.exists() and self.checkpoint_path.is_file()

    def compute_sha256(self) -> Optional[str]:
        """Compute SHA-256 hash of the weight checkpoint."""
        if not self.is_available():
            return None
        if self._weights_hash:
            return self._weights_hash

        sha256 = hashlib.sha256()
        with open(self.checkpoint_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                sha256.update(chunk)
        self._weights_hash = sha256.hexdigest()
        return self._weights_hash

    def load_session(self, preferred_provider: Optional[str] = None) -> bool:
        """Load and cache the ONNX Runtime session with provider fallback to CPU."""
        if not self.is_available():
            self._session = None
            self._execution_provider = "None"
            return False

        # Verify integrity hash if expected hash is configured
        computed_hash = self.compute_sha256()
        if self.expected_sha256 and computed_hash != self.expected_sha256:
            raise ValueError(
                f"Model integrity failure: expected SHA-256 {self.expected_sha256}, got {computed_hash}"
            )

        # Provider selection: prefer user request or CUDA if available, fallback cleanly to CPU
        available_providers = ort.get_available_providers()
        providers = []
        if preferred_provider and preferred_provider in available_providers:
            providers.append(preferred_provider)
        if "CUDAExecutionProvider" in available_providers and preferred_provider != "CPUExecutionProvider":
            providers.append("CUDAExecutionProvider")
        if "CPUExecutionProvider" not in providers:
            providers.append("CPUExecutionProvider")

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        try:
            self._session = ort.InferenceSession(
                str(self.checkpoint_path),
                sess_options=sess_options,
                providers=providers,
            )
            self._execution_provider = self._session.get_providers()[0]
            return True
        except Exception as exc:
            # Fallback strictly to CPU execution provider
            try:
                self._session = ort.InferenceSession(
                    str(self.checkpoint_path),
                    sess_options=sess_options,
                    providers=["CPUExecutionProvider"],
                )
                self._execution_provider = "CPUExecutionProvider"
                return True
            except Exception as cpu_exc:
                self._session = None
                self._execution_provider = "None"
                print(f"[ONNXInferenceEngine] Failed to load session for {self.model_id}: {cpu_exc}")
                return False

    def predict_image(
        self,
        image: Image.Image,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
    ) -> dict[str, Any]:
        """Execute end-to-end forward pass on PIL Image and decode detections."""
        if not self.is_available():
            return {
                "status": ModelAvailabilityStatus.MODEL_UNAVAILABLE.value,
                "error": f"Model checkpoint missing at {self.checkpoint_rel_path}",
                "findings": [],
                "latency_ms": None,
                "provenance": self.get_provenance().model_dump(),
            }

        if self._session is None:
            if not self.load_session():
                return {
                    "status": ModelAvailabilityStatus.ERROR.value,
                    "error": f"Failed to initialize ONNX Runtime session for {self.model_id}",
                    "findings": [],
                    "latency_ms": None,
                    "provenance": self.get_provenance().model_dump(),
                }

        conf_th = conf_threshold if conf_threshold is not None else self.conf_threshold
        iou_th = iou_threshold if iou_threshold is not None else self.iou_threshold

        try:
            # 1. Aspect-ratio preserving letterbox preprocessing
            tensor, meta = ImagePreprocessor.letterbox(image, target_size=self.input_size)

            # 2. Forward pass with high-resolution latency tracking
            input_name = self._session.get_inputs()[0].name
            t0 = time.perf_counter()
            outputs = self._session.run(None, {input_name: tensor})
            t1 = time.perf_counter()
            latency_ms = round((t1 - t0) * 1000.0, 2)

            # 3. Postprocess and unletterbox detections
            raw_output = outputs[0]
            detections = decode_yolo_detections(
                raw_output=raw_output,
                meta=meta,
                class_names=self.class_names,
                conf_threshold=conf_th,
                iou_threshold=iou_th,
            )

            return {
                "status": ModelAvailabilityStatus.AVAILABLE.value,
                "findings": detections,
                "latency_ms": latency_ms,
                "execution_provider": self._execution_provider,
                "provenance": self.get_provenance().model_dump(),
                "letterbox_meta": {
                    "original_width": meta.original_width,
                    "original_height": meta.original_height,
                    "scale": meta.scale,
                    "pad_x": meta.pad_x,
                    "pad_y": meta.pad_y,
                },
            }
        except Exception as exc:
            return {
                "status": ModelAvailabilityStatus.ERROR.value,
                "error": f"Inference execution failed: {str(exc)}",
                "findings": [],
                "latency_ms": None,
                "provenance": self.get_provenance().model_dump(),
            }

    def get_provenance(self) -> ModelProvenance:
        """Produce auditable provenance record."""
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
