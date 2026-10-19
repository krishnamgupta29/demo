"""Study management API endpoints: upload, retrieve, preview, and archive."""

from pathlib import Path
from typing import Optional
from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from backend.config import settings
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
):
  """Retrieve paginated list of ingested dental studies."""
  return study_service.list_studies(
      limit=limit, offset=offset, include_archived=include_archived
  )


@router.get(
    "/{study_id}",
    response_model=StudyDetail,
    summary="Retrieve full details of a specific study",
)
def get_study(study_id: str):
  """Retrieve comprehensive study record including findings and quality assessment."""
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
      filename=f"{study_id}_preview.png",
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
  success = study_service.delete_study(study_id, hard_delete=hard_delete)
  if not success:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Study with ID '{study_id}' was not found",
    )
  return None
