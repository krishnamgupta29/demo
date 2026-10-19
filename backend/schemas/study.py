"""Study and radiograph intake schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import Field, field_validator
from .base import ClinicalBaseModel
from .clinician import ClinicianConfirmation
from .finding import PathologyFinding
from .tooth import ToothBox


class StudyStatus(str, Enum):
  """Lifecycle status of a dental imaging study."""

  INGESTED = "ingested"
  SCREENED = "screened"
  REVIEWED = "reviewed"
  ARCHIVED = "archived"


class RadiographMetadata(ClinicalBaseModel):
  """Extracted technical parameters from the ingested dental radiograph."""

  original_filename: str = Field(..., description="Uploaded file name")
  storage_rel_path: str = Field(
      ..., description="Relative path within local data storage"
  )
  preview_rel_path: Optional[str] = Field(
      default=None, description="Relative path to generated web preview raster"
  )
  file_size_bytes: int = Field(..., ge=0, description="Exact file size in bytes")
  sha256_hash: str = Field(
      ..., description="Cryptographic SHA-256 hash of raw image payload"
  )
  mime_type: str = Field(
      ..., description="Detected MIME type (image/png, image/jpeg, etc.)"
  )
  width_px: int = Field(
      ..., ge=1, description="Image horizontal width in pixels"
  )
  height_px: int = Field(
      ..., ge=1, description="Image vertical height in pixels"
  )
  aspect_ratio: float = Field(
      ..., gt=0.0, description="Aspect ratio: width / height"
  )
  is_dicom: bool = Field(
      default=False, description="Flag indicating if image arrived as DICOM"
  )
  metadata_sanitized: bool = Field(
      default=True,
      description="Flag asserting all EXIF/DICOM PHI has been stripped",
  )


class ImageQualityAssessment(ClinicalBaseModel):
  """Quality screening assessment for panoramic radiograph validity."""

  passed: bool = Field(
      default=True, description="Overall quality pass/fail flag"
  )
  blur_score_variance: Optional[float] = Field(
      default=None, description="Laplacian variance blur score"
  )
  aspect_ratio_valid: bool = Field(
      default=True,
      description="True if aspect ratio matches panoramic profile (>= 1.35)",
  )
  resolution_valid: bool = Field(
      default=True, description="True if resolution meets minimum (>= 900x450)"
  )
  warnings: list[str] = Field(
      default_factory=list, description="Quality caution advisories"
  )


class StudyCreate(ClinicalBaseModel):
  """Parameters submitted when registering a new study."""

  patient_anonymous_id: Optional[str] = Field(
      default=None,
      description="Anonymous patient identifier (e.g., 'PT-8834')",
  )
  acquisition_date: Optional[str] = Field(
      default=None, description="Date of radiograph exposure (YYYY-MM-DD)"
  )
  clinical_indication: Optional[str] = Field(
      default=None,
      description="Reason for exam (e.g., 'Routine checkup', 'Tooth 16 pain')",
  )


class StudyResponse(ClinicalBaseModel):
  """Standard summary response for a registered study."""

  study_id: str = Field(..., description="Unique case study UUID: CASE-[UUID8]")
  patient_anonymous_id: str = Field(..., description="Anonymous patient code")
  status: StudyStatus = Field(
      default=StudyStatus.INGESTED, description="Study lifecycle status"
  )
  created_at: datetime = Field(
      default_factory=datetime.utcnow, description="Study intake timestamp"
  )
  radiograph: RadiographMetadata = Field(
      ..., description="Radiograph file metadata"
  )
  quality: ImageQualityAssessment = Field(
      default_factory=ImageQualityAssessment,
      description="Image quality screening assessment",
  )


class StudyDetail(StudyResponse):
  """Comprehensive study payload including tooth localizations and findings."""

  teeth: list[ToothBox] = Field(
      default_factory=list,
      description="Detected or verified permanent teeth in FDI notation",
  )
  findings: list[PathologyFinding] = Field(
      default_factory=list,
      description="Detected or verified dental pathology findings",
  )
  confirmation: Optional[ClinicianConfirmation] = Field(
      default=None, description="Clinician review and attestation record"
  )
  archived: bool = Field(
      default=False, description="Archive flag for soft-deleted studies"
  )


class StudyList(ClinicalBaseModel):
  """Paginated or listed collection of study summaries."""

  total: int = Field(..., ge=0, description="Total number of studies in query")
  items: list[StudyResponse] = Field(
      default_factory=list, description="List of study summaries"
  )
