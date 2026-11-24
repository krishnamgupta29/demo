"""Test suite verifying pretrained model registry, contracts, and MODEL_UNAVAILABLE defaults."""

import numpy as np
import pytest
from backend.services.model_adapter import model_registry, ModelTask
from backend.schemas.provenance import ModelAvailabilityStatus


def test_model_registry_registered_candidates():
  """Verify that all 4 priority dental AI models are registered."""
  models = model_registry.list_models()
  registered_ids = {m["model_id"] for m in models}

  expected_ids = {
      "abychkov-fdi-detection",
      "liodon-panoramic-screener",
      "nsitnov-dental-segmentation",
      "boneloss-pan769-baseline",
  }
  assert expected_ids.issubset(registered_ids), f"Missing models: {expected_ids - registered_ids}"


def test_uninstalled_models_report_model_unavailable():
  """Enforce truthful reporting: uninstalled checkpoints MUST be MODEL_UNAVAILABLE."""
  models = {m["model_id"]: m for m in model_registry.list_models()}
  uninstalled_ids = ["nsitnov-dental-segmentation", "boneloss-pan769-baseline"]
  for mid in uninstalled_ids:
    m = models[mid]
    assert m["is_available"] is False
    assert m["availability_status"] == ModelAvailabilityStatus.MODEL_UNAVAILABLE.value
    assert m["weights_hash_sha256"] is None


def test_installed_models_report_available():
  """Enforce truthful reporting: verified installed checkpoints report AVAILABLE with SHA-256."""
  models = {m["model_id"]: m for m in model_registry.list_models()}
  installed_ids = ["liodon-panoramic-screener", "abychkov-fdi-detection"]
  for mid in installed_ids:
    m = models[mid]
    assert m["is_available"] is True
    assert m["availability_status"] == ModelAvailabilityStatus.AVAILABLE.value
    assert m["weights_hash_sha256"] is not None
    assert len(m["weights_hash_sha256"]) == 64


def test_zero_fake_predictions():
  """Enforce that inference requests on uninstalled models return MODEL_UNAVAILABLE without fake predictions."""
  for mid in ["nsitnov-dental-segmentation", "boneloss-pan769-baseline"]:
    adapter = model_registry.get_adapter(mid)
    assert adapter is not None

    dummy_tensor = np.zeros(adapter.entry.input_shape, dtype=np.float32)
    result = adapter.run_inference(dummy_tensor)

    assert result["status"] == ModelAvailabilityStatus.MODEL_UNAVAILABLE.value
    assert "error" in result
    assert "outputs" not in result or result.get("outputs") is None


def test_model_endpoint_api(client):
  """Verify /api/v1/models endpoint returns truthful registry listings."""
  response = client.get("/api/v1/models")
  assert response.status_code == 200
  data = response.json()
  assert data["total"] >= 4
  assert "External checkpoints require explicit user authorization" in data["notice"]

  statuses = {m["model_id"]: m["availability_status"] for m in data["models"]}
  assert statuses["nsitnov-dental-segmentation"] == "MODEL_UNAVAILABLE"
  assert statuses["boneloss-pan769-baseline"] == "MODEL_UNAVAILABLE"
  assert statuses["liodon-panoramic-screener"] == "AVAILABLE"
  assert statuses["abychkov-fdi-detection"] == "AVAILABLE"


def test_specific_model_status_api(client):
  """Verify /api/v1/models/{model_id}/status endpoint."""
  # Uninstalled model check
  response_uninstalled = client.get("/api/v1/models/nsitnov-dental-segmentation/status")
  assert response_uninstalled.status_code == 200
  data_un = response_uninstalled.json()
  assert data_un["model_id"] == "nsitnov-dental-segmentation"
  assert data_un["is_available"] is False
  assert data_un["provenance"]["availability_status"] == "MODEL_UNAVAILABLE"

  # Installed model check
  response_installed = client.get("/api/v1/models/liodon-panoramic-screener/status")
  assert response_installed.status_code == 200
  data_in = response_installed.json()
  assert data_in["model_id"] == "liodon-panoramic-screener"
  assert data_in["is_available"] is True
  assert data_in["provenance"]["availability_status"] == "AVAILABLE"
  assert len(data_in["provenance"]["weights_hash_sha256"]) == 64

