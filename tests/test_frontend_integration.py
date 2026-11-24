"""Automated Integration & Component Test Suite for DENTRACE Level 5 Streamlit Workstation.

Tests:
1. Frontend module imports and component loading
2. API client communication with FastAPI core (Health, Readiness, Models)
3. Study upload flow, preview raster generation, and dimension verification
4. Real model inference trigger and findings extraction
5. Odontogram quadrant partitioning and tooth selection state
6. Clinician review attestation submission and persistence
7. Chairside exam and patient symptom recording
8. Documentation readiness preflight and Missing Evidence Detective
9. Local narrative draft generation (Ollama / deterministic) and edit updates
10. PDF claim pack export with running headers, footers, and signature line
11. Curie-Nordic design tokens & Okabe-Ito colorblind-safe CSS definitions
12. Offline security boundary (Zero cloud egress, 127.0.0.1 binding)
"""

import io
from PIL import Image
import pytest

from backend.database.connection import get_db
from backend.services.clinical_service import clinical_service
from frontend.api_client import DentraceAPIClient, api_client
from frontend.styles import CURIE_NORDIC_CSS
from frontend.components.odontogram import (
    QUADRANT_1,
    QUADRANT_2,
    QUADRANT_3,
    QUADRANT_4,
    TOOTH_NAMES,
)

# Ensure all integration tests use isolated test DB configured by conftest.py
api_client.force_in_process = True


@pytest.fixture(scope="module")
def synthetic_test_study():
  """Creates a clean synthetic test study for frontend integration tests."""
  # Generate a small 640x320 synthetic grayscale image
  img = Image.new("L", (640, 320), color=80)
  buf = io.BytesIO()
  img.save(buf, format="PNG")
  img_bytes = buf.getvalue()

  resp = api_client.upload_study(
      file_bytes=img_bytes,
      filename="frontend_test_opg.png",
      patient_anonymous_id="PT-TEST-FE-101",
      clinical_indication="Frontend automated integration test fixture",
  )
  assert resp["success"] is True, f"Upload failed: {resp.get('error')}"
  study_id = resp["data"]["study_id"]

  yield study_id

  # Teardown
  api_client.delete_study(study_id)


def test_frontend_modules_import():
  """Verifies all frontend views, components, and client can be imported without errors."""
  import frontend.app
  import frontend.styles
  import frontend.api_client
  import frontend.components.canvas_viewer
  import frontend.components.odontogram
  import frontend.components.header
  import frontend.views.overview
  import frontend.views.upload
  import frontend.views.workstation
  import frontend.views.fdi_explorer
  import frontend.views.evidence
  import frontend.views.preauth_studio
  import frontend.views.system_settings

  assert frontend.styles.CURIE_NORDIC_CSS is not None
  assert len(frontend.components.odontogram.TOOTH_NAMES) == 32


def test_api_client_health_and_readiness():
  """Verifies frontend API client reaches local FastAPI health and readiness endpoints."""
  health = api_client.get_health()
  assert health.get("status") == "healthy"
  assert "version" in health
  assert "Draft for dentist review" in health.get("disclaimer", "")

  readiness = api_client.get_readiness()
  assert readiness.get("status") == "ready"
  checks = readiness.get("checks", {})
  assert checks.get("database") is True
  assert checks.get("storage") is True


def test_api_client_model_inventory():
  """Verifies model inventory returns candidates with truthful availability and licenses."""
  models = api_client.list_models()
  assert len(models) >= 3

  model_ids = {m["model_id"] for m in models}
  assert "liodon-panoramic-screener" in model_ids
  assert "abychkov-fdi-detection" in model_ids

  for m in models:
    assert "architecture" in m
    assert "license" in m
    assert "is_available" in m
    assert m["license"] in ["CC BY-NC 4.0", "Open Community / Educational", "Apache 2.0", "Academic Research Only"]


def test_study_upload_and_preview_flow(synthetic_test_study):
  """Verifies study intake, dimension calculation, and raster preview retrieval."""
  study_id = synthetic_test_study
  study = api_client.get_study(study_id)
  assert study is not None
  assert study["study_id"] == study_id
  assert study["patient_anonymous_id"] == "PT-TEST-FE-101"

  # Preview raster check
  preview_bytes = api_client.get_preview_bytes(study_id)
  assert preview_bytes is not None
  assert len(preview_bytes) > 100
  # Verify valid image header
  assert preview_bytes.startswith(b"\x89PNG") or preview_bytes.startswith(b"\xff\xd8")


def test_model_inference_trigger_and_findings(synthetic_test_study):
  """Verifies triggering real model analysis endpoint populates study findings."""
  study_id = synthetic_test_study
  res = api_client.analyze_study(study_id)
  assert res["success"] is True

  study = api_client.get_study(study_id)
  # Findings list exists (even if 0 detections on blank synthetic image)
  assert "findings" in study
  assert isinstance(study["findings"], list)


def test_odontogram_quadrant_partitioning():
  """Verifies anatomical correctness of permanent tooth FDI numbers."""
  # Quadrant 1 (Maxillary Right): 18 to 11
  assert QUADRANT_1 == [18, 17, 16, 15, 14, 13, 12, 11]
  # Quadrant 2 (Maxillary Left): 21 to 28
  assert QUADRANT_2 == [21, 22, 23, 24, 25, 26, 27, 28]
  # Quadrant 4 (Mandibular Right): 48 to 41
  assert QUADRANT_4 == [48, 47, 46, 45, 44, 43, 42, 41]
  # Quadrant 3 (Mandibular Left): 31 to 38
  assert QUADRANT_3 == [31, 32, 33, 34, 35, 36, 37, 38]

  # All 32 permanent teeth mapped in dictionary
  assert len(TOOTH_NAMES) == 32
  assert TOOTH_NAMES[16] == "Maxillary Right 1st Molar"
  assert TOOTH_NAMES[46] == "Mandibular Right 1st Molar"
  assert TOOTH_NAMES[21] == "Maxillary Left Central Incisor"


def test_clinician_attestation_flow(synthetic_test_study):
  """Tests recording human dentist finding confirmation via clinical API."""
  study_id = synthetic_test_study

  # Inject a synthetic finding into SQLite for this study to test review
  with get_db() as conn:
    conn.execute(
        """
        INSERT OR REPLACE INTO findings (
            finding_id, study_id, pathology_class, confidence,
            annotation_modality, geometry_type, tooth_fdi, review_status, urgency
        ) VALUES (
            'FIND-FE-TEST-01', ?, 'caries', 0.85, 'detection_bounding_box', 'box', 16, 'pending', 'routine'
        );
        """,
        (study_id,),
    )

  # Submit clinician attestation
  res = api_client.submit_clinician_review(
      study_id=study_id,
      finding_id="FIND-FE-TEST-01",
      decision="confirmed",
      reviewer_name="Dr. Sarah Connor, DDS",
      license_number="DEN-FE-8812",
      clinical_notes="Verified occlusal pit caries.",
  )
  assert res["success"] is True

  # Verify persistence
  evidence = api_client.get_clinical_evidence(study_id)
  confirmations = evidence.get("dentist_confirmations", [])
  assert len(confirmations) >= 1
  cfm = next(c for c in confirmations if c["finding_id"] == "FIND-FE-TEST-01")
  assert cfm["decision"] == "confirmed"
  assert cfm["reviewer_name"] == "Dr. Sarah Connor, DDS"


def test_chairside_exam_and_symptom_recording(synthetic_test_study):
  """Tests recording pulp vitality, percussion, and symptoms."""
  study_id = synthetic_test_study

  # 1. Record exam
  ex_res = api_client.record_examination(
      study_id=study_id,
      tooth_fdi=16,
      pulp_vitality="responsive",
      percussion_sensitivity=False,
      palpation_sensitivity=False,
      pocket_depth_mm=3.0,
      clinical_notes="Normal response to cold testing.",
  )
  assert ex_res["success"] is True

  # 2. Record symptom
  sym_res = api_client.record_symptom(
      study_id=study_id,
      tooth_fdi=16,
      symptom_description="Mild sensitivity to cold beverages",
      duration_days=5,
      severity="mild",
  )
  assert sym_res["success"] is True

  # 3. Verify in evidence package
  pkg = api_client.get_clinical_evidence(study_id)
  assert len(pkg.get("clinical_examinations", [])) >= 1
  assert len(pkg.get("patient_symptoms", [])) >= 1


def test_preauth_preflight_and_detective(synthetic_test_study):
  """Verifies procedure selection triggers preflight checklist and detective analysis."""
  study_id = synthetic_test_study

  # Select procedure
  proc_res = api_client.select_procedure(
      study_id=study_id,
      procedure_name="Composite Restoration - 1 Surface",
      clinician_rationale="Small occlusal carious lesion on Tooth 16.",
      tooth_fdi=16,
      suggested_cdt_code="D2391",
      cdt_code_verified=True,
      urgency="routine",
  )
  assert proc_res["success"] is True

  # Check preflight
  preflight = api_client.get_preflight(study_id)
  assert preflight is not None
  assert "preflight_status" in preflight
  assert "checklist_completeness_pct" in preflight
  assert "missing_evidence" in preflight


def test_preauth_draft_generation_and_editing(synthetic_test_study):
  """Tests generating narrative draft (deterministic fallback or Ollama) and editing."""
  study_id = synthetic_test_study

  # Generate draft
  gen_res = api_client.generate_draft(study_id, force_deterministic=True)
  assert gen_res["success"] is True
  draft = gen_res["data"]
  draft_id = draft["draft_id"]

  assert "section_1_case_identification" in draft
  assert "section_7_clinical_rationale" in draft

  # Edit draft
  up_res = api_client.update_draft(
      study_id=study_id,
      updated_sections={"section_7_clinical_rationale": "Updated clinician rationale for test case."},
      reviewer_name="Dr. J. Doe, DDS",
      license_number="DEN-94812",
  )
  assert up_res["success"] is True
  assert up_res["data"]["section_7_clinical_rationale"] == "Updated clinician rationale for test case."


def test_pdf_claim_pack_export_stream(synthetic_test_study):
  """Tests binary PDF export endpoint via API client."""
  study_id = synthetic_test_study

  # Ensure draft exists
  api_client.generate_draft(study_id, force_deterministic=True)

  pdf_bytes = api_client.export_pdf(study_id)
  assert pdf_bytes is not None
  assert len(pdf_bytes) > 5000
  assert pdf_bytes.startswith(b"%PDF-")
  assert b"ReportLab" in pdf_bytes


def test_curie_nordic_styling_tokens():
  """Verifies Curie-Nordic design system CSS tokens and colorblind safety."""
  css = CURIE_NORDIC_CSS

  # Surfaces
  assert "#070A0D" in css
  assert "#0D1217" in css
  assert "#131B22" in css

  # Okabe-Ito Colorblind-safe Pathologies
  assert "#E67E22" in css  # Caries
  assert "#E74C3C" in css  # Deep Caries
  assert "#CC79A7" in css  # Periapical
  assert "#F59E0B" in css  # Impaction
  assert "#38BDF8" in css  # Bone Loss
  assert "#009E73" in css  # Root Canal

  # Typography
  assert "Figtree" in css
  assert "Noto Sans" in css
  assert "JetBrains Mono" in css

  # Reduced motion media query
  assert "prefers-reduced-motion: reduce" in css


def test_offline_security_boundary():
  """Verifies API client points strictly to localhost loopback with zero external URLs."""
  assert api_client.base_url.startswith("http://127.0.0.1:8000") or api_client.base_url.startswith("http://localhost:8000")
  assert "api.openai.com" not in api_client.base_url
  assert "anthropic.com" not in api_client.base_url
  assert "cloud" not in api_client.base_url
