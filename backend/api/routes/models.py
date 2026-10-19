"""Model registry and truthful availability status endpoints."""

from fastapi import APIRouter, HTTPException, status
from backend.services.model_adapter import model_registry

router = APIRouter(prefix="/models", tags=["Model Registry"])


@router.get("", summary="List candidate models and truthful availability status")
def list_models():
  """List all registered candidate models with real status on local filesystem.

  Enforces truthful representation: if weight file is missing, returns
  MODEL_UNAVAILABLE.
  """
  return {
      "total": len(model_registry.list_models()),
      "models": model_registry.list_models(),
      "notice": (
          "External checkpoints require explicit user authorization before"
          " downloading to host."
      ),
  }


@router.get("/{model_id}/status", summary="Get specific model status")
def get_model_status(model_id: str):
  """Retrieve status, SHA-256 weight hash, and provenance of a specific model candidate."""
  entry = model_registry.get_entry(model_id)
  if not entry:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Model '{model_id}' is not registered in the system",
    )

  prov = entry.get_provenance()
  return {
      "model_id": entry.model_id,
      "model_name": entry.model_name,
      "version": entry.version,
      "is_available": entry.is_available(),
      "weight_path": entry.weight_rel_path,
      "weights_hash_sha256": prov.weights_hash_sha256,
      "provenance": prov.model_dump(),
  }
