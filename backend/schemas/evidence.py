"""Clinical evidence schemas for DENTRACE Level 4.

Defines strongly typed, unmergeable models separating:
A. AI-observed radiographic findings (unverified until clinician review)
B. Dentist-confirmed clinical findings & examination details (authoritative human facts)
C. Insurance documentation requirements & pre-auth narrative trace citations
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import Field, field_validator
from .base import ClinicalBaseModel
from .finding import (
    AnnotationModality,
    FindingBoundingBox,
    FindingPolygon,
    PathologyClass,
    UrgencyLevel,
)
from .clinician import ReviewDecision
from .tooth import VALID_FDI_TEETH


class EvidenceSource(str, Enum):
  """Authoritative source provenance for any clinical statement or finding."""

  AI_RADIOGRAPHIC_OBSERVATION = "ai_radiographic_observation"
  CLINICIAN_CONFIRMATION = "clinician_confirmation"
  CLINICIAN_EXAMINATION = "clinician_examination"
  PATIENT_SYMPTOM = "patient_symptom"
  CLINICAL_RATIONALE = "clinical_rationale"
  PAYER_REQUIREMENT = "payer_requirement"


class VerificationStatus(str, Enum):
  """Verification lifecycle status of clinical facts."""

  UNVERIFIED_AI_SUSPICION = "unverified_ai_suspicion"
  CONFIRMED_BY_CLINICIAN = "confirmed_by_clinician"
  REJECTED_BY_CLINICIAN = "rejected_by_clinician"
  MODIFIED_BY_CLINICIAN = "modified_by_clinician"
  UNSUPPORTED_CLAIM = "unsupported_claim"


class PreflightStatus(str, Enum):
  """Deterministic document-readiness state for clinical and insurance review."""

  READY_FOR_CLINICIAN_REVIEW = "READY_FOR_CLINICIAN_REVIEW"
  INCOMPLETE_DOCUMENTATION = "INCOMPLETE_DOCUMENTATION"
  REQUIRES_ADDITIONAL_EVIDENCE = "REQUIRES_ADDITIONAL_EVIDENCE"
  REQUIRES_CODE_VERIFICATION = "REQUIRES_CODE_VERIFICATION"
  BLOCKED_BY_UNCONFIRMED_TOOTH = "BLOCKED_BY_UNCONFIRMED_TOOTH"
  REVIEWED_DRAFT_READY_FOR_EXPORT = "REVIEWED_DRAFT_READY_FOR_EXPORT"


class DraftState(str, Enum):
  """Pre-authorization narrative lifecycle state."""

  INITIAL_DRAFT = "initial_draft"
  INCOMPLETE_DOCUMENTATION = "incomplete_documentation"
  READY_FOR_CLINICIAN_REVIEW = "ready_for_clinician_review"
  CLINICIAN_REVISED = "clinician_revised"
  REVIEWED_DRAFT_READY_FOR_EXPORT = "reviewed_draft_ready_for_export"


# ==============================================================================
# Concept A: AI-observed radiographic findings
# ==============================================================================

class RadiographicObservation(ClinicalBaseModel):
  """Unverified AI-observed radiographic finding with full spatial and provenance context."""

  evidence_id: str = Field(..., description="Unique evidence UUID: EVID-RAD-[UUID8]")
  study_id: str = Field(..., description="Associated study UUID")
  radiograph_id: str = Field(..., description="Target radiograph ID")
  finding_id: str = Field(..., description="Corresponding finding UUID")
  pathology_candidate: PathologyClass = Field(..., description="Model-proposed pathology class")
  confidence: float = Field(..., ge=0.0, le=1.0, description="Raw model confidence score")
  calibrated_confidence: Optional[float] = Field(
      default=None,
      ge=0.0,
      le=1.0,
      description="Calibrated probability if available; never equated to clinical truth without calibration",
  )
  annotation_modality: AnnotationModality = Field(
      ..., description="Geometry modality: instance_segmentation vs detection_bounding_box"
  )
  geometry_semantics: str = Field(
      default="abnormal_tooth_boundary",
      description="Clinical meaning of geometry (e.g. abnormal tooth contour, NOT microscopic margin)",
  )
  bbox: Optional[FindingBoundingBox] = Field(default=None)
  polygon: Optional[FindingPolygon] = Field(default=None)
  tooth_fdi: Optional[int] = Field(default=None, description="Host tooth FDI number (11-48) or None if uncertain")
  fdi_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
  fdi_uncertain: bool = Field(default=False, description="Flag indicating tooth number is ambiguous or shifted")
  fdi_uncertainty_reason: Optional[str] = Field(default=None)
  image_crop_path: Optional[str] = Field(default=None, description="Local disk path to annotated crop")
  model_id: str = Field(..., description="Vision model identifier")
  model_version: str = Field(..., description="Vision model version")
  provenance_run_id: Optional[str] = Field(default=None)
  source_type: EvidenceSource = Field(default=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION, frozen=True)
  verification_status: VerificationStatus = Field(
      default=VerificationStatus.UNVERIFIED_AI_SUSPICION,
      description="Must remain unverified until explicit clinician review",
  )

  @field_validator("tooth_fdi")
  @classmethod
  def check_fdi(cls, v: Optional[int]) -> Optional[int]:
    if v is not None and v not in VALID_FDI_TEETH:
      raise ValueError(f"Invalid host tooth FDI: {v}")
    return v


# ==============================================================================
# Concept B: Dentist-confirmed clinical findings and examinations
# ==============================================================================

class DentistFindingConfirmation(ClinicalBaseModel):
  """Authoritative human clinician attestation on a specific AI finding."""

  evidence_id: str = Field(..., description="Unique confirmation UUID: EVID-CFM-[UUID8]")
  finding_id: str = Field(..., description="Target finding UUID")
  reviewer_name: str = Field(..., description="Full legal name of reviewing dental practitioner")
  license_number: str = Field(..., description="Practitioner license number")
  decision: ReviewDecision = Field(..., description="CONFIRMED, REJECTED, or MODIFIED")
  confirmed_fdi: Optional[int] = Field(
      default=None,
      description="Clinician-verified FDI tooth number (overrides AI suggestion)",
  )
  confirmed_pathology: Optional[PathologyClass] = Field(
      default=None,
      description="Clinician-verified pathology taxonomy",
  )
  review_timestamp: datetime = Field(default_factory=datetime.utcnow)
  clinical_notes: Optional[str] = Field(default=None)
  source_type: EvidenceSource = Field(default=EvidenceSource.CLINICIAN_CONFIRMATION, frozen=True)
  verification_status: VerificationStatus = Field(...)

  @field_validator("confirmed_fdi")
  @classmethod
  def check_fdi(cls, v: Optional[int]) -> Optional[int]:
    if v is not None and v not in VALID_FDI_TEETH:
      raise ValueError(f"Invalid confirmed tooth FDI: {v}")
    return v


class ClinicalExaminationRecord(ClinicalBaseModel):
  """Objective dental chairside examination findings entered by the clinician."""

  evidence_id: str = Field(..., description="Unique examination UUID: EVID-EXM-[UUID8]")
  tooth_fdi: Optional[int] = Field(default=None)
  pulp_vitality: Optional[str] = Field(
      default=None,
      description="'responsive', 'non_vital', 'delayed', or 'not_tested'",
  )
  percussion_sensitivity: Optional[bool] = Field(default=None)
  palpation_sensitivity: Optional[bool] = Field(default=None)
  probing_depth_mm: Optional[float] = Field(default=None, ge=0.0, le=20.0)
  mobility_grade: Optional[int] = Field(default=None, ge=0, le=3)
  visual_cavitation: Optional[bool] = Field(default=None)
  defective_restoration: Optional[bool] = Field(default=None)
  swelling_or_fistula: Optional[bool] = Field(default=None)
  source_type: EvidenceSource = Field(default=EvidenceSource.CLINICIAN_EXAMINATION, frozen=True)
  recorded_by: Optional[str] = Field(default=None)
  recorded_at: datetime = Field(default_factory=datetime.utcnow)


class PatientSymptomRecord(ClinicalBaseModel):
  """Patient-reported symptoms recorded during intake."""

  evidence_id: str = Field(..., description="Unique symptom UUID: EVID-SYM-[UUID8]")
  chief_complaint: Optional[str] = Field(default=None)
  pain_character: Optional[str] = Field(
      default=None,
      description="'sharp', 'dull', 'throbbing', 'spontaneous', 'cold_sensitive', 'none'",
  )
  pain_onset_duration: Optional[str] = Field(default=None)
  mastication_pain: Optional[bool] = Field(default=None)
  source_type: EvidenceSource = Field(default=EvidenceSource.PATIENT_SYMPTOM, frozen=True)
  recorded_at: datetime = Field(default_factory=datetime.utcnow)


# ==============================================================================
# Concept C: Insurance documentation requirements & procedure requests
# ==============================================================================

class RequestedProcedureRecord(ClinicalBaseModel):
  """Clinician-requested procedure with justification and optional candidate CDT code."""

  procedure_id: str = Field(..., description="Unique procedure UUID: PROC-[UUID8]")
  tooth_fdi: Optional[int] = Field(default=None, description="Target tooth FDI number")
  procedure_name: str = Field(..., description="Name of requested dental treatment")
  suggested_cdt_code: Optional[str] = Field(
      default=None,
      description="Optional illustrative candidate CDT code (must be verified by clinician)",
  )
  cdt_code_verified_by_dentist: bool = Field(
      default=False,
      description="Mandatory clinician attestation on CDT code suitability",
  )
  clinician_rationale: str = Field(..., description="Practitioner justification based on clinical need")
  urgency: UrgencyLevel = Field(default=UrgencyLevel.ROUTINE)
  source_type: EvidenceSource = Field(default=EvidenceSource.CLINICAL_RATIONALE, frozen=True)
  selected_by: Optional[str] = Field(default=None)


class PayerPolicyTemplate(ClinicalBaseModel):
  """Payer-specific pre-authorization documentation requirements."""

  payer_id: str = Field(default="DEFAULT_ACADEMIC_STANDARD")
  payer_name: str = Field(default="Academic Dental Pre-Authorization Standard")
  requires_confirmed_tooth: bool = Field(default=True)
  requires_radiograph_attachment: bool = Field(default=True)
  requires_clinician_rationale: bool = Field(default=True)
  procedure_checklist: dict[str, list[str]] = Field(
      default_factory=lambda: {
          "endodontics": [
              "periapical_radiograph",
              "pulp_vitality_test",
              "percussion_sensitivity",
              "clinician_rationale",
          ],
          "restorative": [
              "radiographic_caries_depth",
              "visual_cavitation_or_symptoms",
              "clinician_rationale",
          ],
          "oral_surgery": [
              "radiographic_angulation",
              "impaction_classification",
              "symptom_or_pathology_evidence",
              "clinician_rationale",
          ],
          "periodontics": [
              "periodontal_probing_depth",
              "radiographic_bone_resorption",
              "clinician_rationale",
          ],
      }
  )
  notes: str = Field(
      default="Illustrative academic checklist rules. Does not guarantee coverage or reimbursement.",
      frozen=True,
  )


# ==============================================================================
# Detective & Readiness Schemas
# ==============================================================================

class MissingEvidenceItem(ClinicalBaseModel):
  """Specific missing clinical datum identified by the detective."""

  item_id: str = Field(...)
  target_field: str = Field(..., description="Identifier of missing fact (e.g., 'pulp_vitality')")
  target_tooth_fdi: Optional[int] = Field(default=None)
  clinical_reason: str = Field(..., description="Why this evidence is medically or administratively required")
  question_prompt: str = Field(..., description="Targeted question to ask the clinician")
  severity: str = Field(default="REQUIRED", description="'REQUIRED' or 'RECOMMENDED'")


class EvidenceReadinessReport(ClinicalBaseModel):
  """Structured preflight report detailing evidence completeness and blocking issues."""

  study_id: str = Field(...)
  preflight_status: PreflightStatus = Field(...)
  checklist_completeness_pct: float = Field(
      ...,
      ge=0.0,
      le=100.0,
      description="Checklist completeness percentage (NOT an insurance approval probability)",
  )
  passed_checks: list[str] = Field(default_factory=list)
  failed_checks: list[str] = Field(default_factory=list)
  missing_evidence: list[MissingEvidenceItem] = Field(default_factory=list)
  unconfirmed_tooth_ids: list[int] = Field(default_factory=list)
  contradictions_detected: list[str] = Field(default_factory=list)
  can_generate_draft: bool = Field(default=False)
  can_export_reviewed_pack: bool = Field(default=False)


# ==============================================================================
# Narrative Statement & Full Pre-Auth Draft Schemas
# ==============================================================================

class NarrativeStatementCitation(ClinicalBaseModel):
  """Traceable sentence linking narrative text directly to verified evidence IDs."""

  statement_id: str = Field(..., description="Unique statement UUID: STMT-[UUID8]")
  section_index: int = Field(..., ge=1, le=10)
  section_title: str = Field(...)
  sentence_text: str = Field(...)
  cited_evidence_ids: list[str] = Field(
      default_factory=list,
      description="IDs of underlying radiographic, confirmation, exam, or rationale evidence",
  )
  source_types: list[EvidenceSource] = Field(default_factory=list)
  verification_status: VerificationStatus = Field(...)
  uncertainty_preserved: bool = Field(
      default=True,
      description="True if radiographic suspicions were correctly qualified as suspected",
  )


class InsurancePreAuthDraft(ClinicalBaseModel):
  """Complete 10-section pre-authorization draft with full evidence traceability."""

  draft_id: str = Field(..., description="Unique draft UUID: DRAFT-[UUID8]")
  study_id: str = Field(...)
  radiograph_id: str = Field(...)
  draft_state: DraftState = Field(default=DraftState.INITIAL_DRAFT)

  # Mandatory 10 clinical sections
  section_1_case_identification: str = Field(...)
  section_2_requested_procedure: str = Field(...)
  section_3_tooth_identifier: str = Field(...)
  section_4_clinician_confirmed_findings: str = Field(...)
  section_5_radiographic_observations: str = Field(...)
  section_6_supporting_evidence_references: str = Field(...)
  section_7_clinical_rationale: str = Field(...)
  section_8_missing_information: str = Field(...)
  section_9_procedure_code_references: str = Field(...)
  section_10_required_reviewer_attestation: str = Field(...)

  # Bidirectional Traceability citations
  statements: list[NarrativeStatementCitation] = Field(default_factory=list)

  # Generation & audit metadata
  generated_by: str = Field(default="deterministic_fallback")
  generation_timestamp: datetime = Field(default_factory=datetime.utcnow)
  last_edited_by_dentist: Optional[str] = Field(default=None)
  last_edited_at: Optional[datetime] = Field(default=None)
  dentist_reviewed: bool = Field(default=False)
  dentist_signature_name: Optional[str] = Field(default=None)
  dentist_signature_timestamp: Optional[datetime] = Field(default=None)


class ClinicalEvidencePackage(ClinicalBaseModel):
  """Aggregated container packaging all clinical facts for preflight and narrative synthesis."""

  package_id: str = Field(..., description="Unique package UUID: PKG-[UUID8]")
  study_id: str = Field(...)
  radiograph_id: str = Field(...)
  created_at: datetime = Field(default_factory=datetime.utcnow)

  # Three distinct separated layers
  ai_observations: list[RadiographicObservation] = Field(default_factory=list)
  dentist_confirmations: list[DentistFindingConfirmation] = Field(default_factory=list)
  clinical_examinations: list[ClinicalExaminationRecord] = Field(default_factory=list)
  patient_symptoms: list[PatientSymptomRecord] = Field(default_factory=list)
  requested_procedures: list[RequestedProcedureRecord] = Field(default_factory=list)
  payer_template: PayerPolicyTemplate = Field(default_factory=PayerPolicyTemplate)


# ==============================================================================
# API Request / Input DTO Schemas
# ==============================================================================

class ClinicianReviewRequest(ClinicalBaseModel):
  """Input payload for dentist attestation on an AI finding."""

  reviewer_name: str = Field(..., description="Full practitioner name")
  license_number: str = Field(..., description="Dental license number")
  decision: ReviewDecision = Field(..., description="'confirmed', 'rejected', or 'modified'")
  confirmed_fdi: Optional[int] = Field(default=None, description="Verified tooth FDI (11-48)")
  confirmed_pathology: Optional[PathologyClass] = Field(default=None)
  clinical_notes: Optional[str] = Field(default=None)


class ClinicalExaminationRequest(ClinicalBaseModel):
  """Input payload for chairside examination observations."""

  tooth_fdi: Optional[int] = Field(default=None)
  pulp_vitality: Optional[str] = Field(default=None, description="'responsive', 'non_vital', 'delayed', or 'not_tested'")
  percussion_sensitivity: Optional[bool] = Field(default=None)
  palpation_sensitivity: Optional[bool] = Field(default=None)
  probing_depth_mm: Optional[float] = Field(default=None, ge=0.0, le=20.0)
  mobility_grade: Optional[int] = Field(default=None, ge=0, le=3)
  visual_cavitation: Optional[bool] = Field(default=None)
  defective_restoration: Optional[bool] = Field(default=None)
  swelling_or_fistula: Optional[bool] = Field(default=None)
  recorded_by: Optional[str] = Field(default=None)


class PatientSymptomRequest(ClinicalBaseModel):
  """Input payload for patient symptoms during intake."""

  chief_complaint: Optional[str] = Field(default=None)
  pain_character: Optional[str] = Field(default=None)
  pain_onset_duration: Optional[str] = Field(default=None)
  mastication_pain: Optional[bool] = Field(default=None)


class ProcedureSelectionRequest(ClinicalBaseModel):
  """Input payload for selecting a proposed clinical procedure."""

  tooth_fdi: Optional[int] = Field(default=None)
  procedure_name: str = Field(...)
  suggested_cdt_code: Optional[str] = Field(default=None)
  cdt_code_verified_by_dentist: bool = Field(default=False)
  clinician_rationale: str = Field(..., min_length=5)
  urgency: UrgencyLevel = Field(default=UrgencyLevel.ROUTINE)
  selected_by: Optional[str] = Field(default=None)


class PreAuthDraftUpdateRequest(ClinicalBaseModel):
  """Input payload for dentist revision of an existing pre-auth draft."""

  dentist_name: str = Field(...)
  license_number: Optional[str] = Field(default=None)
  section_1_case_identification: Optional[str] = None
  section_2_requested_procedure: Optional[str] = None
  section_3_tooth_identifier: Optional[str] = None
  section_4_clinician_confirmed_findings: Optional[str] = None
  section_5_radiographic_observations: Optional[str] = None
  section_6_supporting_evidence_references: Optional[str] = None
  section_7_clinical_rationale: Optional[str] = None
  section_8_missing_information: Optional[str] = None
  section_9_procedure_code_references: Optional[str] = None
  section_10_required_reviewer_attestation: Optional[str] = None


class PatientInfoPayload(ClinicalBaseModel):
  """Structured patient intake information for presentation-ready clinical reporting."""

  patient_name: str = Field(..., min_length=1, description="Patient full name")
  patient_id: str = Field(..., min_length=1, description="Patient case code / MRN")
  age: int = Field(..., gt=0, lt=150, description="Patient age in years (positive integer)")
  sex: Optional[str] = Field(default=None, description="Biological sex ('male', 'female', 'other', 'unspecified')")
  scan_date: str = Field(..., min_length=4, description="Examination / scan date (YYYY-MM-DD)")
  chief_complaint: Optional[str] = Field(default=None, description="Patient's primary stated complaint")
  symptoms: Optional[str] = Field(default=None, description="Reported clinical symptoms")
  history: Optional[str] = Field(default=None, description="Relevant clinical / dental history")
  referring_dentist: Optional[str] = Field(default=None, description="Referring clinician or clinic name")


class ClaimReportRequest(ClinicalBaseModel):
  """Comprehensive payload for generating a presentation-ready 4-page clinical report."""

  patient_info: Optional[PatientInfoPayload] = Field(default=None, description="Patient demographic and clinical intake data")
  custom_narrative: Optional[str] = Field(default=None, description="Dentist-edited clinical justification narrative")
  snapshot_3d_base64: Optional[str] = Field(default=None, description="Base64-encoded PNG snapshot of 3D anatomy viewer")
  selected_fdi: Optional[int] = Field(default=None, description="FDI tooth selected in 3D snapshot")
  selected_pathology: Optional[str] = Field(default=None, description="Pathology associated with 3D snapshot")


