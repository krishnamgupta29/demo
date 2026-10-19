"""Health and readiness diagnostic endpoints."""

from datetime import datetime
import shutil
from fastapi import APIRouter, Response, status
from backend.config import settings
from backend.database.connection import get_db
from backend.services.model_adapter import model_registry

router = APIRouter(tags=["System Diagnostics"])


@router.get("/health", summary="Liveness probe")
def health_check():
  """Liveness probe verifying application process is responsive."""
  return {
      "status": "healthy",
      "app": settings.APP_NAME,
      "version": settings.APP_VERSION,
      "environment": settings.ENVIRONMENT,
      "timestamp": datetime.utcnow().isoformat(),
      "disclaimer": settings.MANDATORY_DISCLAIMER,
  }


@router.get("/readiness", summary="Service readiness probe")
@router.get("/ready", summary="Readiness probe", include_in_schema=False)
def readiness_check(response: Response):
  """Readiness probe evaluating database connectivity, storage writeability, and models."""
  checks = {
      "database": False,
      "storage": False,
      "models": "evaluated",
  }

  # 1. Check database connectivity
  try:
    with get_db() as conn:
      row = conn.execute("SELECT 1 as alive;").fetchone()
      if row and row["alive"] == 1:
        checks["database"] = True
  except Exception as exc:
    checks["database_error"] = str(exc)

  # 2. Check storage writeability
  try:
    test_file = settings.DATA_DIR / ".readiness_probe"
    test_file.write_text("probe")
    test_file.unlink()
    checks["storage"] = True
  except Exception as exc:
    checks["storage_error"] = str(exc)

  # 3. Check disk space on C:
  stat = shutil.disk_usage("C:/")
  free_gb = round(stat.free / (1024**3), 2)
  checks["disk_free_gb"] = free_gb

  # 4. Truthful model registry summary
  models_summary = model_registry.list_models()
  available_models = [m["model_id"] for m in models_summary if m["is_available"]]
  checks["available_models"] = available_models
  checks["total_registered_models"] = len(models_summary)

  all_ready = checks["database"] and checks["storage"]
  if not all_ready:
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

  return {
      "status": "ready" if all_ready else "degraded",
      "checks": checks,
      "timestamp": datetime.utcnow().isoformat(),
      "disclaimer": settings.MANDATORY_DISCLAIMER,
  }
