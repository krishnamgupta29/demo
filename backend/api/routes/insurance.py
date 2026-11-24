"""Insurance Pre-Authorization, CDT Coding, and PDF Export Endpoints for DENTRACE Level 4.

Provides RESTful endpoints for:
1. Grounded pre-authorization narrative generation (Ollama + fallback).
2. Pre-authorization draft retrieval and clinician revision.
3. Local ReportLab PDF claim pack rendering and export.
4. Demonstrative ADA CDT catalog metadata inspection.
"""

import base64
import logging
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Path, Query, Response, status
from fastapi.responses import Response

from ...schemas.evidence import (
    InsurancePreAuthDraft,
    PreAuthDraftUpdateRequest,
    ClaimReportRequest,
)

logger = logging.getLogger(__name__)
from ...clinical.cdt_coding import CDTCodingService, DEMO_CDT_CATALOG, CDT_CATALOG_VERSION, CDT_CATALOG_SOURCE
from ...services.clinical_service import clinical_service

router = APIRouter(prefix="/insurance", tags=["Insurance Pre-Authorization"])


@router.post(
    "/studies/{study_id}/draft",
    response_model=dict[str, Any],
    summary="Generate evidence-grounded pre-authorization narrative draft",
)
def generate_draft(
    study_id: str = Path(..., description="Target study UUID"),
    force_regenerate: bool = Query(
        False, description="If true, overwrite existing clinician-edited draft"
    ),
    model_tag: str = Query(
        "qwen2.5:3b", description="Local Ollama model tag to use"
    ),
):
  """Generates 10-section pre-authorization draft grounded strictly in structured evidence."""
  try:
    draft, metrics = clinical_service.generate_pre_auth_draft(
        study_id=study_id,
        force_regenerate=force_regenerate,
        model_tag=model_tag,
    )
    return {
        "draft": draft.model_dump(),
        "performance_metrics": metrics,
    }
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to generate pre-authorization draft: {exc}",
    )


@router.get(
    "/studies/{study_id}/draft",
    response_model=Optional[InsurancePreAuthDraft],
    summary="Retrieve existing pre-authorization draft",
)
def get_draft(
    study_id: str = Path(..., description="Target study UUID"),
):
  """Retrieves persisted pre-authorization draft, or returns null if not generated yet."""
  draft = clinical_service.get_pre_auth_draft(study_id)
  if not draft:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No pre-authorization draft generated for study '{study_id}'.",
    )
  return draft


@router.put(
    "/studies/{study_id}/draft",
    response_model=InsurancePreAuthDraft,
    summary="Revise pre-authorization narrative (Dentist editing)",
)
def update_draft(
    study_id: str = Path(..., description="Target study UUID"),
    req: PreAuthDraftUpdateRequest = ...,
):
  """Updates draft sections with clinician edits and marks state as CLINICIAN_REVISED."""
  try:
    return clinical_service.update_pre_auth_draft(study_id, req)
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to update pre-authorization draft: {exc}",
    )


@router.get(
    "/studies/{study_id}/claim-pack/pdf",
    summary="Export local ReportLab PDF claim pack",
)
def export_claim_pack_pdf(
    study_id: str = Path(..., description="Target study UUID"),
):
  """Renders multi-page clinical claim pack PDF with watermarks and dentist signature block."""
  try:
    pdf_bytes = clinical_service.export_claim_pack_pdf(study_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=DENTRACE_{study_id}_ClaimPack.pdf"
        },
    )
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to render claim pack PDF: {exc}",
    )


@router.post(
    "/studies/{study_id}/claim-pack/pdf",
    summary="Generate & export presentation-ready ReportLab PDF claim pack",
)
def generate_custom_claim_pack_pdf(
    study_id: str = Path(..., description="Target study UUID"),
    req: ClaimReportRequest = ...,
):
  """Renders customized 4-page clinical assessment & pre-auth pack with patient info, 3D snapshot, and edited narrative."""
  try:
    snapshot_bytes = None
    if req.snapshot_3d_base64:
      try:
        raw_b64 = req.snapshot_3d_base64.split(",")[-1]
        snapshot_bytes = base64.b64decode(raw_b64)
      except Exception as ex:
        logger.warning(f"Failed to decode 3D snapshot base64: {ex}")

    # Persist patient info if provided
    if req.patient_info:
      clinical_service.save_patient_info(study_id, req.patient_info)

    pdf_bytes = clinical_service.export_claim_pack_pdf(
        study_id=study_id,
        patient_info=req.patient_info,
        custom_narrative=req.custom_narrative,
        snapshot_3d_bytes=snapshot_bytes,
        selected_fdi=req.selected_fdi,
        selected_pathology=req.selected_pathology,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=DENTRACE_{study_id}_ClinicalReport.pdf"
        },
    )
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to render custom claim pack PDF: {exc}",
    )



@router.get(
    "/cdt/catalog",
    summary="Retrieve demonstrative ADA CDT coding catalog metadata",
)
def get_cdt_catalog():
  """Returns demonstrative academic CDT code catalog with licensing notices."""
  return {
      "version": CDT_CATALOG_VERSION,
      "source": CDT_CATALOG_SOURCE,
      "disclaimer": "Demo code subset for academic research only; verify against official current ADA CDT set.",
      "codes": [code.model_dump() for code in DEMO_CDT_CATALOG.values()],
  }
