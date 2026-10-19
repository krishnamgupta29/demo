"""Model provenance and prediction source schemas."""

from enum import Enum
from typing import Optional
from pydantic import Field
from .base import ClinicalBaseModel


class PredictionSource(str, Enum):
  """Source authority that generated a clinical observation."""

  AI_MODEL = "ai_model"
  DETERMINISTIC_RULE = "deterministic_rule"
  CLINICIAN_MANUAL = "clinician_manual"
  HISTORICAL_RECORD = "historical_record"


class ModelAvailabilityStatus(str, Enum):
  """Truthful status of model availability (Never fabricate a prediction when unavailable)."""

  AVAILABLE = "AVAILABLE"
  MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
  INITIALIZING = "INITIALIZING"
  ERROR = "ERROR"


class ModelProvenance(ClinicalBaseModel):
  """Immutable metadata tracing the exact model checkpoint that produced a prediction."""

  model_id: str = Field(
      ...,
      description="Unique identifier of the model (e.g., 'liodon-panoramic-v1')",
  )
  model_name: str = Field(
      ..., description="Human-readable model name", examples=["YOLO11n-Dental"]
  )
  model_version: str = Field(
      ..., description="Version tag of model weights", examples=["1.0.0"]
  )
  weights_hash_sha256: Optional[str] = Field(
      default=None,
      description="Cryptographic SHA-256 hash of the `.onnx` or `.pt` weight file",
  )
  execution_provider: str = Field(
      default="CPUExecutionProvider",
      description="Runtime execution provider: CPUExecutionProvider or CUDAExecutionProvider",
  )
  source_type: PredictionSource = Field(
      default=PredictionSource.AI_MODEL,
      description="Source authority for this prediction",
  )
  inference_latency_ms: Optional[float] = Field(
      default=None,
      ge=0.0,
      description="Measured forward inference time in milliseconds (Never fabricated)",
  )
  availability_status: ModelAvailabilityStatus = Field(
      default=ModelAvailabilityStatus.AVAILABLE,
      description="Operational availability status",
  )
