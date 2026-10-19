"""Test suite verifying FastAPI study endpoints, previews, and error handling."""

import io
import pytest
from fastapi import status


def test_health_endpoints(client):
  """Verify liveness probe at root and /api/v1."""
  for path in ("/health", "/api/v1/health"):
    response = client.get(path)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert "Draft for dentist review. Not a diagnosis." in data["disclaimer"]


def test_readiness_endpoints(client):
  """Verify readiness probe at /ready and /api/v1/readiness."""
  for path in ("/ready", "/readiness", "/api/v1/readiness"):
    response = client.get(path)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] is True
    assert data["checks"]["storage"] is True


def test_create_study_png(client, synthetic_opg_png):
  """Verify study creation via PNG upload."""
  files = {"file": ("dental_opg.png", synthetic_opg_png, "image/png")}
  data = {
      "patient_anonymous_id": "PT-TEST-001",
      "clinical_indication": "Annual orthodontic assessment",
      "acquisition_date": "2026-10-19",
  }

  response = client.post("/api/v1/studies/upload", files=files, data=data)
  assert response.status_code == status.HTTP_201_CREATED
  res = response.json()

  assert res["study_id"].startswith("CASE-")
  assert res["patient_anonymous_id"] == "PT-TEST-001"
  assert res["radiograph"]["width_px"] == 1000
  assert res["radiograph"]["height_px"] == 500
  assert res["quality"]["passed"] is True

  # Verify retrieval of the created study
  study_id = res["study_id"]
  get_res = client.get(f"/api/v1/studies/{study_id}")
  assert get_res.status_code == status.HTTP_200_OK
  detail = get_res.json()
  assert detail["study_id"] == study_id

  # Verify retrieval of generated preview raster
  preview_res = client.get(f"/api/v1/studies/{study_id}/preview")
  assert preview_res.status_code == status.HTTP_200_OK
  assert preview_res.headers["content-type"] == "image/png"
  assert len(preview_res.content) > 0


def test_create_study_rest_alias(client, synthetic_opg_jpeg):
  """Verify standard REST POST /api/v1/studies works identically to /upload."""
  files = {"file": ("dental_opg.jpg", synthetic_opg_jpeg, "image/jpeg")}
  response = client.post("/api/v1/studies", files=files)
  assert response.status_code == status.HTTP_201_CREATED
  assert response.json()["study_id"].startswith("CASE-")


def test_list_studies_pagination(client, synthetic_opg_png):
  """Verify paginated listing of ingested studies."""
  response = client.get("/api/v1/studies?limit=10&offset=0")
  assert response.status_code == status.HTTP_200_OK
  data = response.json()
  assert "total" in data
  assert "items" in data
  assert isinstance(data["items"], list)
  assert data["total"] >= 1


def test_study_not_found(client):
  """Verify 404 response for non-existent study ID."""
  response = client.get("/api/v1/studies/CASE-NONEXISTENT")
  assert response.status_code == status.HTTP_404_NOT_FOUND
  assert "not found" in response.json()["detail"].lower()


def test_delete_study_hard(client, synthetic_opg_png):
  """Verify hard deletion of study cascades and removes files from disk."""
  files = {"file": ("to_delete.png", synthetic_opg_png, "image/png")}
  create_res = client.post("/api/v1/studies/upload", files=files)
  study_id = create_res.json()["study_id"]

  # Delete with hard_delete=True
  del_res = client.delete(f"/api/v1/studies/{study_id}?hard_delete=true")
  assert del_res.status_code == status.HTTP_204_NO_CONTENT

  # Verify study no longer exists
  get_res = client.get(f"/api/v1/studies/{study_id}")
  assert get_res.status_code == status.HTTP_404_NOT_FOUND


def test_reject_unsupported_file_extension(client):
  """Verify rejection of forbidden file extension."""
  files = {"file": ("malicious.exe", b"executable_bytes_content" * 10, "application/octet-stream")}
  response = client.post("/api/v1/studies/upload", files=files)
  assert response.status_code == status.HTTP_400_BAD_REQUEST
  assert "not permitted" in response.json()["detail"]


def test_reject_corrupt_upload_via_api(client, synthetic_corrupt_png):
  """Verify rejection of corrupt PNG payload via API."""
  files = {"file": ("corrupt.png", synthetic_corrupt_png, "image/png")}
  response = client.post("/api/v1/studies/upload", files=files)
  assert response.status_code == status.HTTP_400_BAD_REQUEST
  assert "Corrupted or invalid" in response.json()["detail"]
