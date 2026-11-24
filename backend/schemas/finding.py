"""Dental anomaly finding schemas, distinguishing segmentation polygons from bounding boxes."""

from enum import Enum
from typing import Optional
from pydantic import Field, field_validator
from .base import ClinicalBaseModel
from .tooth import VALID_FDI_TEETH


class PathologyClass(str, Enum):
  """Authoritative dental anomaly taxonomy supported by DENTRACE."""

  CARIES = "caries"
  DEEP_CARIES = "deep_caries"
  PERIAPICAL_LESION = "periapical_lesion"
  IMPACTED_TOOTH = "impacted_tooth"
  ALVEOLAR_BONE_LOSS = "alveolar_bone_loss"
  ROOT_CANAL_TREATMENT = "root_canal_treatment"
  TREATED_TOOTH_WITH_RADIOLUCENCY = "treated_tooth_with_radiolucency"


class AnnotationModality(str, Enum):
  """Explicit modality distinguishing true pixel segmentations from detection fallbacks."""

  INSTANCE_SEGMENTATION = "instance_segmentation"
  DETECTION_BOUNDING_BOX = "detection_bounding_box"
  CRESTAL_POLYLINE = "crestal_polyline"


class UrgencyLevel(str, Enum):
  """Clinical attention urgency assigned authoritatively by deterministic rules."""

  ROUTINE = "routine"
  SOON = "soon"
  URGENT = "urgent"


class FindingBoundingBox(ClinicalBaseModel):
  """Rectangular bounding region for detection fallbacks."""

  x_min: float = Field(..., ge=0.0)
  y_min: float = Field(..., ge=0.0)
  x_max: float = Field(..., gt=0.0)
  y_max: float = Field(..., gt=0.0)

  @field_validator("x_max")
  @classmethod
  def check_x(cls, v: float, info) -> float:
    if "x_min" in info.data and v <= info.data["x_min"]:
      raise ValueError("x_max must be greater than x_min")
    return v

  @field_validator("y_max")
  @classmethod
  def check_y(cls, v: float, info) -> float:
    if "y_min" in info.data and v <= info.data["y_min"]:
      raise ValueError("y_max must be greater than y_min")
    return v

  @property
  def area(self) -> float:
    return (self.x_max - self.x_min) * (self.y_max - self.y_min)


class FindingPolygon(ClinicalBaseModel):
  """Pixel-accurate polygon vertices for instance segmentation."""

  points: list[list[float]] = Field(
      ...,
      min_length=3,
      description="List of [x, y] coordinates in pixel space tracing pathology boundary",
  )

  @field_validator("points")
  @classmethod
  def check_points(cls, pts: list[list[float]]) -> list[list[float]]:
    for pt in pts:
      if len(pt) != 2:
        raise ValueError(f"Each vertex must have exactly 2 coordinates: {pt}")
      if pt[0] < 0 or pt[1] < 0:
        raise ValueError(
            f"Coordinates must be non-negative pixel values: {pt}"
        )
    return pts


class ClinicalEvidence(ClinicalBaseModel):
  """Supporting radiographic observations grounded in image facts."""

  radiographic_density: str = Field(
      default="radiolucent",
      description="Visual radiographic density: radiolucent, radiopaque, or mixed",
  )
  affected_surface: Optional[str] = Field(
      default=None,
      description="Anatomical tooth surface: occlusal, mesial, distal, cervical, periapical",
  )
  observed_features: list[str] = Field(
      default_factory=list,
      description="Specific radiographic observations (e.g., 'crestal bone resorption')",
  )
  diagnostic_requirement: Optional[str] = Field(
      default=None,
      description="Mandatory clinical imaging requirement (e.g., 'Needs intraoral periapical radiograph')",
  )


class PathologyFinding(ClinicalBaseModel):
  """An individual pathology finding identified on a panoramic radiograph."""

  finding_id: str = Field(..., description="Unique finding UUID: FIND-[UUID8]")
  study_id: str = Field(..., description="Associated study UUID")
  tooth_fdi: Optional[int] = Field(
      default=None,
      description="Associated host permanent tooth in FDI notation (11-48), or None for quadrant findings",
  )
  pathology_class: PathologyClass = Field(
      ..., description="Standardized pathology condition"
  )
  annotation_modality: AnnotationModality = Field(
      ...,
      description="True instance segmentation vs detection bounding box vs polyline",
  )
  confidence: float = Field(
      ..., ge=0.0, le=1.0, description="Detection confidence score"
  )
  urgency: UrgencyLevel = Field(
      default=UrgencyLevel.ROUTINE,
      description="Clinical urgency assigned by deterministic rule layer",
  )
  bbox: Optional[FindingBoundingBox] = Field(
      default=None, description="Bounding box (required for detection fallbacks)"
  )
  polygon: Optional[FindingPolygon] = Field(
      default=None,
      description="Pixel segmentation polygon (required for instance segmentation)",
  )
  has_mask: bool = Field(
      default=False,
      description="Whether this finding has a genuine instance segmentation polygon mask",
  )
  fdi_uncertain: bool = Field(
      default=False,
      description="True if FDI tooth number is AI-estimated with low confidence or ambiguous overlap",
  )
  fdi_status: str = Field(
      default="ai_estimated",
      description="FDI verification status: 'clinician_confirmed' or 'ai_estimated'",
  )
  evidence: ClinicalEvidence = Field(
      default_factory=ClinicalEvidence,
      description="Objective radiographic facts",
  )
  suggested_procedure: Optional[str] = Field(
      default=None, description="Illustrative procedure category"
  )
  demo_cdt_code: Optional[str] = Field(
      default=None, description="Illustrative demo CDT code from config"
  )

  @field_validator("tooth_fdi")
  @classmethod
  def check_fdi(cls, v: Optional[int]) -> Optional[int]:
    if v is not None and v not in VALID_FDI_TEETH:
      raise ValueError(f"Invalid host tooth FDI number: {v}")
    return v

  @field_validator("polygon")
  @classmethod
  def check_modality_polygon(
      cls, v: Optional[FindingPolygon], info
  ) -> Optional[FindingPolygon]:
    if (
        info.data.get("annotation_modality")
        == AnnotationModality.INSTANCE_SEGMENTATION
        and v is None
    ):
      raise ValueError(
          "polygon is required when annotation_modality is"
          " instance_segmentation"
      )
    return v
