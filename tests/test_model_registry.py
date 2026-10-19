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
  models = model_registry.list_models()
  for m in models:
    assert m["is_available"] is False
    assert m["availability_status"] == ModelAvailabilityStatus.MODEL_UNAVAILABLE.value
    assert m["weights_hash_sha256"] is None


def test_zero_fake_predictions():
  """Enforce that inference requests on uninstalled models return MODEL_UNAVAILABLE without fake predictions."""
  for mid in ["abychkov-fdi-detection", "liodon-panoramic-screener", "nsitnov-dental-segmentation"]:
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

  for m in data["models"]:
    assert m["availability_status"] == "MODEL_UNAVAILABLE"


def test_specific_model_status_api(client):
  """Verify /api/v1/models/{model_id}/status endpoint."""
  response = client.get("/api/v1/models/abychkov-fdi-detection/status")
  assert response.status_code == 200
  data = response.json()
  assert data["model_id"] == "abychkov-fdi-detection"
  assert data["is_available"] is False
  assert data["provenance"]["availability_status"] == "MODEL_UNAVAILABLE"
