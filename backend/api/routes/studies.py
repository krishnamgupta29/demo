"""Study management API endpoints: upload, retrieve, preview, and archive."""

from pathlib import Path
import re
from typing import Optional
from pydantic import BaseModel
from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, Response
from backend.config import settings
from backend.schemas.analysis import AnalysisRequest, AnalysisResponse
from backend.schemas.finding import PathologyFinding
from backend.schemas.study import StudyDetail, StudyList, StudyResponse
from backend.services.study_service import study_service
from backend.storage.file_manager import storage_manager

router = APIRouter(prefix="/studies", tags=["Dental Studies"])


@router.post(
    "",
    response_model=StudyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create/upload a study (REST standard)",
    include_in_schema=False,
)
@router.post(
    "/upload",
    response_model=StudyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new dental panoramic radiograph",
)
async def upload_study(
    file: UploadFile = File(..., description="Dental radiograph image file"),
    patient_anonymous_id: Optional[str] = Form(
        None, description="Optional anonymous patient code"
    ),
    clinical_indication: Optional[str] = Form(
        None, description="Optional exam notes or indication"
    ),
    acquisition_date: Optional[str] = Form(
        None, description="Optional acquisition date (YYYY-MM-DD)"
    ),
    modality: Optional[str] = Form(
        None, description="Optional radiograph modality: panoramic_opg, intraoral_periapical, bitewing, unknown"
    ),
):
  """Validate, sanitize, persist radiograph bytes, and create a study record."""
  if not file.filename:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Missing file name"
    )

  # Check extension against allowed list
  ext = Path(file.filename).suffix.lower()
  if ext not in settings.ALLOWED_EXTENSIONS:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            f"File extension '{ext}' is not permitted. Allowed:"
            f" {sorted(settings.ALLOWED_EXTENSIONS)}"
        ),
    )

  raw_bytes = await file.read()
  if len(raw_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
    raise HTTPException(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        detail=(
            f"Payload size exceeds maximum allowed"
            f" ({settings.MAX_UPLOAD_SIZE_BYTES / (1024*1024):.1f} MB)"
        ),
    )

  try:
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename=file.filename,
        patient_anonymous_id=patient_anonymous_id,
        clinical_indication=clinical_indication,
        acquisition_date=acquisition_date,
        modality=modality,
    )
    return study
  except ValueError as exc:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
    ) from exc
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to process study intake: {str(exc)}",
    ) from exc


@router.get(
    "",
    response_model=StudyList,
    summary="List dental studies with pagination",
)
def list_studies(
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    include_archived: bool = Query(
        False, description="Include soft-deleted studies"
    ),
    patient_id: Optional[str] = Query(
        None, description="Filter studies by patient ID"
    ),
):
  """Retrieve paginated list of ingested dental studies, optionally filtered by patient ID."""
  return study_service.list_studies(
      limit=limit,
      offset=offset,
      include_archived=include_archived,
      patient_id=patient_id,
  )


def validate_safe_study_id(study_id: str) -> str:
  """Reject path traversal or invalid study IDs."""
  if not study_id or not re.match(r"^[a-zA-Z0-9_\-]{1,64}$", study_id):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid study identifier format",
    )
  return study_id


@router.get(
    "/{study_id}",
    response_model=StudyDetail,
    summary="Retrieve full details of a specific study",
)
def get_study(study_id: str):
  """Retrieve comprehensive study record including findings and quality assessment."""
  validate_safe_study_id(study_id)
  study = study_service.get_study(study_id)
  if not study:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Study with ID '{study_id}' was not found",
    )
  return study


@router.get(
    "/{study_id}/preview",
    summary="Retrieve web-optimized preview image raster",
)
def get_study_preview(study_id: str):
  """Return generated PNG preview thumbnail for display on web viewer."""
  validate_safe_study_id(study_id)
  study = study_service.get_study(study_id)
  if not study or not study.radiograph.preview_rel_path:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Study preview for '{study_id}' not found",
    )

  preview_path = storage_manager.get_preview_path(
      study.radiograph.preview_rel_path
  )
  if not preview_path or not preview_path.exists():
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Preview raster file missing on disk for '{study_id}'",
    )

  return FileResponse(
      path=preview_path,
      media_type="image/png",
      content_disposition_type="inline",
  )


@router.get(
    "/{study_id}/original",
    summary="Retrieve full-resolution original radiograph raster",
)
def get_study_original(study_id: str):
  """Return original full-resolution radiograph raster for diagnostic precision inspection."""
  validate_safe_study_id(study_id)
  study = study_service.get_study(study_id)
  if not study or not study.radiograph.storage_rel_path:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Study storage record for '{study_id}' not found",
    )

  storage_path = storage_manager.get_storage_path(
      study.radiograph.storage_rel_path
  )
  if not storage_path or not storage_path.exists():
    # Fallback to preview if original storage is missing
    preview_path = storage_manager.get_preview_path(
        study.radiograph.preview_rel_path
    )
    if preview_path and preview_path.exists():
      return FileResponse(
          path=preview_path,
          media_type="image/png",
          content_disposition_type="inline",
      )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Radiograph asset missing on disk for '{study_id}'",
    )

  # If file is DICOM, convert full-resolution pixel array to PNG
  ext = storage_path.suffix.lower()
  if ext in (".dcm", ".dicom") or study.radiograph.is_dicom:
    try:
      import pydicom
      import numpy as np
      from PIL import Image
      import io
      dcm = pydicom.dcmread(str(storage_path), force=True)
      arr = dcm.pixel_array.astype(np.float32)
      photo = getattr(dcm, "PhotometricInterpretation", "MONOCHROME2")
      if photo == "MONOCHROME1":
        arr = np.max(arr) - arr
      min_val, max_val = float(np.min(arr)), float(np.max(arr))
      if max_val > min_val:
        norm = ((arr - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
      else:
        norm = np.zeros_like(arr, dtype=np.uint8)
      img = Image.fromarray(norm)
      buf = io.BytesIO()
      img.save(buf, format="PNG")
      buf.seek(0)
      return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as exc:
      print(f"[studies] DICOM full-resolution conversion fallback: {exc}")

  media_type = study.radiograph.mime_type or "image/png"
  if media_type == "application/dicom":
    media_type = "image/png"

  return FileResponse(
      path=storage_path,
      media_type=media_type,
      content_disposition_type="inline",
  )


@router.delete(
    "/{study_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive or permanently delete a study",
)
def delete_study(
    study_id: str,
    hard_delete: bool = Query(
        False,
        description=(
            "If true, permanently remove files from disk. If false,"
            " soft-archive."
        ),
    ),
):
  """Archive or delete a study and associated assets."""
  validate_safe_study_id(study_id)
  success = study_service.delete_study(study_id, hard_delete=hard_delete)
  if not success:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Study with ID '{study_id}' was not found",
    )
  return None


@router.post(
    "/{study_id}/analyze",
    response_model=AnalysisResponse,
    summary="Execute real dental AI model analysis on study radiograph",
)
def analyze_study(
    study_id: str,
    payload: Optional[AnalysisRequest] = None,
    model_id: Optional[str] = Query(None, description="Registered model ID to execute (overrides payload if specified)"),
):
  """Run real dental AI model inference on study image, persist findings and return auditable predictions.

  - Runs real verified pretrained model (e.g. liodon screener, dentex-yolov8n-seg, nsitnov-8024-seg).
  - Truthfully reports MODEL_UNAVAILABLE if compatible weights or reference landmarks are missing.
  - Distinguishes true instance segmentation polygon masks from bounding box proposals.
  - Persists detected anomalies, calibrated FDI assignments, and execution latency.
  - Enforces clinical safety: strictly avoids automatic diagnosis, treatment, or insurance coding.
  """
  validate_safe_study_id(study_id)
  chosen_model = model_id or (payload.model_id if payload else "liodon-panoramic-screener")
  conf_thresh = payload.conf_threshold if payload else 0.25
  iou_thresh = payload.iou_threshold if payload else 0.35

  try:
    result = study_service.analyze_study(
        study_id=study_id,
        model_id=chosen_model,
        conf_threshold=conf_thresh,
        iou_threshold=iou_thresh,
    )
    return result
  except ValueError as exc:
    if "not found" in str(exc).lower():
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail=str(exc),
      ) from exc
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    ) from exc
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Inference pipeline execution error: {str(exc)}",
    ) from exc


class ModalityUpdateRequest(BaseModel):
  modality: str


class ManualAnnotationRequest(BaseModel):
  tooth_fdi: Optional[int] = None
  pathology_class: str = "caries"
  bbox: dict  # {"x_min": float, "y_min": float, "x_max": float, "y_max": float}
  clinical_notes: Optional[str] = None
  anatomical_structure: Optional[str] = None


@router.patch(
    "/{study_id}/modality",
    response_model=StudyDetail,
    summary="Update or confirm the radiograph modality",
)
def update_study_modality(study_id: str, payload: ModalityUpdateRequest):
  """Update radiograph modality (panoramic_opg, intraoral_periapical, bitewing, unknown)."""
  try:
    success = study_service.update_study_modality(study_id, payload.modality)
    if not success:
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail=f"Study with ID '{study_id}' was not found",
      )
    return study_service.get_study(study_id)
  except ValueError as exc:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{study_id}/annotations",
    response_model=PathologyFinding,
    status_code=status.HTTP_201_CREATED,
    summary="Create clinician-authored manual region annotation",
)
def create_manual_annotation(study_id: str, payload: ManualAnnotationRequest):
  """Persist a clinician-authored region annotation on the radiograph."""
  study = study_service.get_study(study_id)
  if not study:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Study with ID '{study_id}' was not found",
    )
  try:
    finding = study_service.add_manual_annotation(
        study_id=study_id,
        tooth_fdi=payload.tooth_fdi,
        pathology_class=payload.pathology_class,
        bbox=payload.bbox,
        clinical_notes=payload.clinical_notes,
        anatomical_structure=payload.anatomical_structure,
    )
    return finding
  except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Failed to record annotation: {str(exc)}",
    ) from exc


@router.delete(
    "/{study_id}/annotations/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a clinician-authored manual region annotation",
)
def delete_manual_annotation(study_id: str, annotation_id: str):
  """Remove a clinician-authored region annotation."""
  success = study_service.delete_manual_annotation(study_id, annotation_id)
  if not success:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Annotation with ID '{annotation_id}' was not found on study '{study_id}'",
    )
  return None

