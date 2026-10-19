"""Clinician confirmation and review audit event schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import Field
from .base import ClinicalBaseModel


class ReviewDecision(str, Enum):
  """Clinician decision on an individual AI finding or entire study."""

  PENDING_REVIEW = "pending_review"
  CONFIRMED = "confirmed"
  MODIFIED = "modified"
  REJECTED = "rejected"


class PhysicalSignatureStatus(str, Enum):
  """Status of physical pen-and-ink clinician signature for insurance claim submission."""

  REQUIRES_PHYSICAL_SIGNATURE = "requires_physical_signature"
  SIGNED_ON_PAPER = "signed_on_paper"
  DIGITALLY_ACKNOWLEDGED = "digitally_acknowledged"


class ClinicianConfirmation(ClinicalBaseModel):
  """Human-in-the-loop clinical attestation recorded by a licensed dental professional."""

  confirmation_id: str = Field(
      ..., description="Unique attestation UUID: CONF-[UUID8]"
  )
  clinician_name: str = Field(
      ...,
      description="Name of reviewing dental practitioner",
      examples=["Dr. Sarah Jenkins, DDS"],
  )
  license_number: str = Field(
      ...,
      description="State/national dental license registration number",
      examples=["DEN-98421"],
  )
  decision: ReviewDecision = Field(
      default=ReviewDecision.PENDING_REVIEW,
      description="Clinical evaluation outcome",
  )
  review_timestamp: datetime = Field(
      default_factory=datetime.utcnow,
      description="Timestamp of review in UTC",
  )
  clinical_notes: Optional[str] = Field(
      default=None,
      description="Practitioner clinical reasoning and chart notes",
  )
  physical_signature_status: PhysicalSignatureStatus = Field(
      default=PhysicalSignatureStatus.REQUIRES_PHYSICAL_SIGNATURE,
      description="Physical signature verification status",
  )


class ReviewAuditEvent(ClinicalBaseModel):
  """Immutable audit ledger record capturing every clinical review interaction."""

  event_id: str = Field(..., description="Unique audit event UUID: AUD-[UUID8]")
  study_id: str = Field(..., description="Target study UUID")
  event_type: str = Field(
      ...,
      description="Event type: STUDY_INTAKE, FINDING_CONFIRMED, FINDING_REJECTED, NARRATIVE_EDITED, PDF_EXPORTED",
  )
  actor: str = Field(
      ...,
      description="User or system component that triggered the event",
      examples=["clinician", "system", "rule_engine"],
  )
  timestamp: datetime = Field(
      default_factory=datetime.utcnow, description="UTC event timestamp"
  )
  payload: dict[str, Any] = Field(
      default_factory=dict, description="Event-specific metadata"
  )
