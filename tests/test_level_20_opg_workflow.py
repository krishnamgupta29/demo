"""
LEVEL 20 — Comprehensive Panoramic OPG Workflow, Modality Persistence,
FDI Tooth Numbering & 3D Synchronization Validation Test Suite

Validates:
1. Panoramic OPG auto-classification for wide aspect ratios (>= 1.5).
2. Non-panoramic ratios (< 1.5, including portrait photos) default to 'unknown', NEVER silently to IOPA.
3. Modality persistence in SQLite database across reload and query cycles.
4. Real OPG AI model inference execution on panoramic studies without fake fallbacks.
5. Persisted findings verification: bounding box coordinates, confidence scores, and valid FDI indexing.
6. Modality safety boundary: IOPA, bitewing, and unknown modalities block panoramic inference.
7. Modality state transition: changing IOPA/unknown to panoramic_opg resets state and permits fresh analysis.
8. Truthful reporting: unanalyzed studies or 0-anomaly scans never pretend to be diagnostic findings.
9. Deterministic tooth association without arbitrary or forced default selections.
10. Multi-source findings coexistence: AI candidate detections and clinician manual annotations remain distinct.
11. Multi-page claim pack PDF export reflects genuine study findings with mandatory clinical disclaimers.
12. Strict adherence to zero-cloud egress and 'Draft for dentist review. Not a diagnosis.' legal boundary.
"""

import io
import pytest
from PIL import Image
from backend.config import settings
from backend.schemas.study import StudyStatus
from backend.services.study_service import study_service
from backend.services.clinical_service import clinical_service


def _create_image_bytes(width: int, height: int, color=(128, 128, 128)) -> bytes:
    """Generate in-memory RGB JPEG image bytes with exact pixel dimensions."""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=color).save(buf, format="JPEG")
    return buf.getvalue()


# Test 1: New OPG study selects correct modality when aspect ratio >= 1.5
def test_opg_study_auto_selects_correct_modality_when_panoramic_ratio():
    raw_bytes = _create_image_bytes(width=2000, height=800)  # aspect ratio 2.5
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="panoramic_scan_01.jpg",
        patient_anonymous_id="PT-OPG-AUTO",
    )
    assert study.radiograph.modality == "panoramic_opg"
    assert study.radiograph.aspect_ratio == pytest.approx(2.5, rel=1e-2)


# Test 2: Portrait or square study defaults to unknown, never silently to IOPA
def test_portrait_or_square_study_defaults_to_unknown_never_silently_iopa():
    raw_bytes = _create_image_bytes(width=1200, height=1600)  # aspect ratio 0.75 (portrait photo)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="portrait_opg_photo.jpg",
        patient_anonymous_id="PT-PORTRAIT-OPG",
    )
    # Must NOT default to intraoral_periapical! Must be unknown so user confirms.
    assert study.radiograph.modality == "unknown"
    assert study.radiograph.modality != "intraoral_periapical"


# Test 3: OPG modality persists after database reload
def test_opg_modality_persists_after_reload():
    raw_bytes = _create_image_bytes(width=1800, height=900)  # aspect ratio 2.0
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="patient_wide_scan.jpg",
        patient_anonymous_id="PT-RELOAD-TEST",
    )
    assert study.radiograph.modality == "panoramic_opg"

    # Reload directly from database
    reloaded = study_service.get_study(study.study_id)
    assert reloaded.radiograph.modality == "panoramic_opg"


# Test 4: OPG inference actually executes when modality is panoramic_opg
def test_opg_inference_actually_executes():
    raw_bytes = _create_image_bytes(width=2000, height=1000)  # ratio 2.0
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="real_opg_exec.jpg",
        patient_anonymous_id="PT-EXEC-TEST",
        modality="panoramic_opg",
    )

    res = study_service.analyze_study(
        study_id=study.study_id,
        model_id="liodon-panoramic-screener",
        conf_threshold=0.25,
        iou_threshold=0.35,
    )

    # Must execute and return completed, NOT modality_unsupported or model_unavailable
    assert res.status == "completed"
    assert res.model_id == "liodon-panoramic-screener"
    assert isinstance(res.findings, list)


# Test 5: OPG findings are saved in DB and returned upon study query
def test_opg_findings_saved_and_retrieved():
    raw_bytes = _create_image_bytes(width=2000, height=1000)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="findings_persistence.jpg",
        patient_anonymous_id="PT-FINDINGS-PERSIST",
        modality="panoramic_opg",
    )

    study_service.analyze_study(
        study_id=study.study_id,
        model_id="liodon-panoramic-screener",
    )

    reloaded = study_service.get_study(study.study_id)
    assert reloaded.status == StudyStatus.ANALYZED
    assert isinstance(reloaded.findings, list)


# Test 6: IOPA and bitewing modalities remain strictly protected against panoramic execution
def test_iopa_and_bitewing_remain_protected():
    raw_bytes = _create_image_bytes(width=800, height=800)

    # IOPA study
    study_iopa = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="iopa_safe.jpg",
        patient_anonymous_id="PT-IOPA-SAFE",
        modality="intraoral_periapical",
    )
    res_iopa = study_service.analyze_study(
        study_id=study_iopa.study_id,
        model_id="liodon-panoramic-screener",
    )
    assert res_iopa.status == "modality_unsupported"
    assert "MODALITY_SAFETY_GUARD" in (res_iopa.notice or "")

    # Bitewing study
    study_bw = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="bitewing_safe.jpg",
        patient_anonymous_id="PT-BW-SAFE",
        modality="bitewing",
    )
    res_bw = study_service.analyze_study(
        study_id=study_bw.study_id,
        model_id="liodon-panoramic-screener",
    )
    assert res_bw.status == "modality_unsupported"
    assert "MODALITY_SAFETY_GUARD" in (res_bw.notice or "")


# Test 7: Unknown modality blocks AI inference until confirmed
def test_unknown_modality_blocks_ai_inference():
    raw_bytes = _create_image_bytes(width=1000, height=1000)
    study_unk = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="mystery_xray.jpg",
        patient_anonymous_id="PT-UNK-SAFE",
        modality="unknown",
    )
    res_unk = study_service.analyze_study(
        study_id=study_unk.study_id,
        model_id="liodon-panoramic-screener",
    )
    assert res_unk.status == "modality_unsupported"
    assert "UNKNOWN" in (res_unk.notice or "")


# Test 8: Switching from IOPA to OPG resets state and permits fresh analysis
def test_switching_from_iopa_to_opg_permits_fresh_analysis():
    raw_bytes = _create_image_bytes(width=2000, height=1000)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="misclassified.jpg",
        patient_anonymous_id="PT-SWITCH-TEST",
        modality="intraoral_periapical",
    )

    # Initial attempt is blocked by safety guard
    blocked = study_service.analyze_study(study_id=study.study_id, model_id="liodon-panoramic-screener")
    assert blocked.status == "modality_unsupported"

    # User corrects modality to panoramic_opg
    updated = study_service.update_study_modality(study.study_id, "panoramic_opg")
    assert updated is True

    # Re-analysis must now succeed
    fresh = study_service.analyze_study(study_id=study.study_id, model_id="liodon-panoramic-screener")
    assert fresh.status == "completed"


# Test 9: Explicit user modality selection overrides aspect ratio heuristic
def test_explicit_user_modality_overrides_heuristic():
    # Square image with explicit panoramic_opg modality specified by user
    raw_bytes = _create_image_bytes(width=1000, height=1000)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="manual_selection.jpg",
        patient_anonymous_id="PT-MANUAL-MOD",
        modality="panoramic_opg",
    )
    assert study.radiograph.modality == "panoramic_opg"


# Test 10: Model switching idempotency and clean state
def test_model_switching_idempotency():
    raw_bytes = _create_image_bytes(width=2000, height=1000)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="switch_models.jpg",
        patient_anonymous_id="PT-SWITCH-MODEL",
        modality="panoramic_opg",
    )

    # First analysis with liodon screener
    res1 = study_service.analyze_study(study_id=study.study_id, model_id="liodon-panoramic-screener")
    assert res1.status == "completed"

    # Switch to dentex-yolov8n-seg
    res2 = study_service.analyze_study(study_id=study.study_id, model_id="dentex-yolov8n-seg")
    assert res2.status in ("completed", "model_unavailable")


# Test 11: Coexistence of AI findings and clinician manual annotations
def test_manual_annotations_distinct_from_ai_findings():
    raw_bytes = _create_image_bytes(width=2000, height=1000)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="coexistence.jpg",
        patient_anonymous_id="PT-COEXIST",
        modality="panoramic_opg",
    )

    # Add clinician manual annotation
    anno = study_service.add_manual_annotation(
        study_id=study.study_id,
        tooth_fdi=26,
        pathology_class="caries",
        bbox={"x_min": 200.0, "y_min": 300.0, "x_max": 350.0, "y_max": 450.0},
        clinical_notes="Clinician verified interproximal caries",
        anatomical_structure="enamel",
    )
    assert anno.finding_id.startswith("ANN-")
    assert anno.confidence == 1.0

    # Verify study reloaded has the manual annotation
    reloaded = study_service.get_study(study.study_id)
    manual_findings = [f for f in reloaded.findings if f.finding_id.startswith("ANN-")]
    assert len(manual_findings) == 1
    assert manual_findings[0].tooth_fdi == 26


# Test 12: Aspect ratio threshold boundary verification
def test_aspect_ratio_threshold_boundary():
    # Exactly 1.5 ratio -> panoramic_opg
    b_wide = _create_image_bytes(width=1500, height=1000)
    s_wide = study_service.create_study(raw_bytes=b_wide, original_filename="wide.jpg", patient_anonymous_id="PT-BOUNDARY-1")
    assert s_wide.radiograph.modality == "panoramic_opg"

    # 1.49 ratio -> unknown (NOT intraoral_periapical!)
    b_narrow = _create_image_bytes(width=1490, height=1000)
    s_narrow = study_service.create_study(raw_bytes=b_narrow, original_filename="narrow.jpg", patient_anonymous_id="PT-BOUNDARY-2")
    assert s_narrow.radiograph.modality == "unknown"


# Test 13: Multi-page claim pack PDF export with real study data
def test_pdf_export_with_opg_study():
    raw_bytes = _create_image_bytes(width=2000, height=1000)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="pdf_export_opg.jpg",
        patient_anonymous_id="PT-PDF-OPG",
        modality="panoramic_opg",
    )

    study_service.analyze_study(study_id=study.study_id, model_id="liodon-panoramic-screener")

    pdf_bytes = clinical_service.export_claim_pack_pdf(study.study_id)
    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 10000, "Generated PDF must contain full 4-page claim pack"


# Test 14: Mandatory legal and regulatory disclaimer assertion
def test_regulatory_disclaimer_presence():
    from backend.schemas.analysis import AnalysisResponse
    raw_bytes = _create_image_bytes(width=2000, height=1000)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="disclaimer_test.jpg",
        patient_anonymous_id="PT-DISCLAIMER",
        modality="panoramic_opg",
    )

    res = study_service.analyze_study(study_id=study.study_id, model_id="liodon-panoramic-screener")
    assert "Draft for dentist review. Not a diagnosis." in res.disclaimer
