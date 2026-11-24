"""Schemas for study analysis requests, execution status, and truthful findings responses."""

from typing import Optional
from pydantic import Field
from .base import ClinicalBaseModel
from .finding import PathologyFinding
from .tooth import ToothBox


class AnalysisRequest(ClinicalBaseModel):
    """Parameters for on-demand radiograph anomaly detection."""

    model_id: Optional[str] = Field(
        default="liodon-panoramic-screener",
        description="Registered model ID to execute (defaults to verified real screener)",
    )
    conf_threshold: Optional[float] = Field(
        default=0.25,
        ge=0.01,
        le=0.99,
        description="Confidence threshold for anomaly proposal filtering",
    )
    iou_threshold: Optional[float] = Field(
        default=0.35,
        ge=0.01,
        le=0.99,
        description="NMS IoU suppression threshold",
    )


class AnalysisResponse(ClinicalBaseModel):
    """Truthful model execution result distinguishing research predictions from diagnoses."""

    study_id: str
    status: str = Field(..., description="Inference execution status: completed, model_unavailable, or error")
    model_id: str
    model_version: str
    execution_time_ms: Optional[float] = None
    execution_provider: str = "None"
    findings_count: int = 0
    findings: list[PathologyFinding] = Field(default_factory=list)
    teeth: list[ToothBox] = Field(default_factory=list)
    disclaimer: str = "Draft for dentist review. Not a diagnosis."
    notice: str = (
        "Academic decision-support prototype. Does not determine clinical diagnosis, "
        "treatment necessity, urgency, or automated insurance pre-authorization."
    )
