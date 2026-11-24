"""Clinical Intelligence and Evidence API Endpoints for DENTRACE Level 4.

Provides RESTful endpoints for:
1. Evidence package retrieval.
2. Clinician finding confirmation, rejection, and tooth FDI correction.
3. Chairside clinical examination recording.
4. Patient intake symptom recording.
5. Procedure selection and rationale recording.
6. Deterministic documentation readiness preflight checking.
7. Chronological audit history inspection.
"""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Path, status
from ...schemas.evidence import (
    ClinicalEvidencePackage,
    DentistFindingConfirmation,
    ClinicalExaminationRecord,
    PatientSymptomRecord,
    RequestedProcedureRecord,
    EvidenceReadinessReport,
    ClinicianReviewRequest,
    ClinicalExaminationRequest,
    PatientSymptomRequest,
    ProcedureSelectionRequest,
    PatientInfoPayload,
)
from ...services.clinical_service import clinical_service

router = APIRouter(prefix="/clinical", tags=["Clinical Intelligence & Evidence"])


@router.get(
    "/studies/{study_id}/evidence",
    response_model=ClinicalEvidencePackage,
    summary="Retrieve strongly typed clinical evidence package",
)
def get_study_evidence(
    study_id: str = Path(..., description="Target study UUID"),
):
  """Assembles complete ClinicalEvidencePackage separating AI observations, clinician facts, and requirements."""
  try:
    return clinical_service.get_clinical_evidence(study_id)
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to assemble clinical evidence: {exc}",
    )


@router.post(
    "/studies/{study_id}/findings/{finding_id}/review",
    response_model=DentistFindingConfirmation,
    summary="Record clinician review decision on an AI finding",
)
def review_finding(
    study_id: str = Path(..., description="Target study UUID"),
    finding_id: str = Path(..., description="Target finding UUID"),
    req: ClinicianReviewRequest = ...,
):
  """Records human clinician confirmation, rejection, or tooth FDI correction with audit logging."""
  try:
    return clinical_service.record_clinician_review(study_id, finding_id, req)
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to record clinical review: {exc}",
    )


@router.post(
    "/studies/{study_id}/examination",
    response_model=ClinicalExaminationRecord,
    summary="Record chairside clinical examination details",
)
def record_examination(
    study_id: str = Path(..., description="Target study UUID"),
    req: ClinicalExaminationRequest = ...,
):
  """Stores chairside diagnostic observations (vitality, percussion, probing depth, visual cavitation)."""
  try:
    return clinical_service.record_clinical_examination(study_id, req)
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to record examination details: {exc}",
    )


@router.post(
    "/studies/{study_id}/symptoms",
    response_model=PatientSymptomRecord,
    summary="Record patient intake symptoms",
)
def record_symptoms(
    study_id: str = Path(..., description="Target study UUID"),
    req: PatientSymptomRequest = ...,
):
  """Stores patient-reported symptoms, chief complaint, and pain characteristics."""
  try:
    return clinical_service.record_patient_symptoms(study_id, req)
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to record patient symptoms: {exc}",
    )


@router.post(
    "/studies/{study_id}/procedure",
    response_model=RequestedProcedureRecord,
    summary="Select requested clinical procedure with rationale",
)
def select_procedure(
    study_id: str = Path(..., description="Target study UUID"),
    req: ProcedureSelectionRequest = ...,
):
  """Selects proposed dental treatment with candidate CDT cross-check and clinical rationale."""
  try:
    return clinical_service.select_requested_procedure(study_id, req)
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to select clinical procedure: {exc}",
    )


@router.get(
    "/studies/{study_id}/readiness",
    response_model=EvidenceReadinessReport,
    summary="Check deterministic documentation readiness (Preflight)",
)
def check_readiness(
    study_id: str = Path(..., description="Target study UUID"),
):
  """Evaluates evidence completeness, unconfirmed teeth, contradictions, and missing items."""
  try:
    return clinical_service.check_documentation_readiness(study_id)
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to evaluate preflight readiness: {exc}",
    )


@router.get(
    "/studies/{study_id}/audit-trail",
    response_model=list[dict[str, Any]],
    summary="Retrieve chronological audit history for study",
)
def get_audit_trail(
    study_id: str = Path(..., description="Target study UUID"),
):
  """Retrieves chronological audit trail of all ingestion, reviews, edits, and exports."""
  try:
    return clinical_service.get_audit_history(study_id)
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to retrieve audit trail: {exc}",
    )


@router.post(
    "/studies/{study_id}/patient-info",
    response_model=PatientInfoPayload,
    summary="Store structured patient demographics and intake data",
)
def save_patient_info(
    study_id: str = Path(..., description="Target study UUID"),
    req: PatientInfoPayload = ...,
):
  """Stores patient demographic and examination intake data locally without logging PHI."""
  try:
    return clinical_service.save_patient_info(study_id, req)
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to save patient information: {exc}",
    )


@router.get(
    "/studies/{study_id}/patient-info",
    response_model=Optional[PatientInfoPayload],
    summary="Retrieve structured patient demographics",
)
def get_patient_info(
    study_id: str = Path(..., description="Target study UUID"),
):
  """Retrieves persisted patient intake data for a study."""
  return clinical_service.get_patient_info(study_id)

