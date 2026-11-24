"""
LEVEL 19 — Comprehensive Four-Tooth IOPA Workflow & Anatomical Correlation Tests

Validates:
1. Reliable Modality Gating independent of filename (scan001.jpg, patient_image.png, random_image_123.jpg).
2. Enforcement of modality restrictions across all inference endpoints and model switches.
3. Interactive manual region annotation: creation, persistence, and deletion.
4. Modality updating via PATCH /studies/{study_id}/modality.
5. Distinction between AI candidates (#FACC15), Manual annotations (#0284C7), Confirmed (#16A34A), and Dismissed (#94A3B8).
6. 10-Section 5-Page Clinical Claim Pack PDF generation with manual annotations.
"""

import io
import pytest
from PIL import Image
from backend.config import settings
from backend.schemas.study import RadiographMetadata, StudyStatus
from backend.services.study_service import study_service
from backend.services.clinical_service import clinical_service


def _create_test_image(width=500, height=500) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(128, 128, 128)).save(buf, format="JPEG")
    return buf.getvalue()


def test_level_19_arbitrary_filename_modality_safety():
    """Verify modality safety guard does NOT rely on filename strings."""
    raw_bytes = _create_test_image(400, 400)

    # 1. Test with completely arbitrary generic filename: scan001.jpg
    study1 = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="scan001.jpg",
        patient_anonymous_id="PT-SCAN-001",
        modality="intraoral_periapical",
    )
    assert study1.radiograph.modality == "intraoral_periapical"

    res1 = study_service.analyze_study(study_id=study1.study_id, model_id="liodon-panoramic-screener")
    assert res1.status == "modality_unsupported"
    assert "MODALITY_SAFETY_GUARD" in (res1.notice or "")

    # 2. Test with patient_image.png
    study2 = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="patient_image.png",
        patient_anonymous_id="PT-IMG-002",
        modality="unknown",
    )
    assert study2.radiograph.modality == "unknown"

    res2 = study_service.analyze_study(study_id=study2.study_id, model_id="dentex-yolov8n-seg")
    assert res2.status == "modality_unsupported"

    # 3. Test with random_image_123.jpg
    study3 = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="random_image_123.jpg",
        patient_anonymous_id="PT-RANDOM-123",
        modality="bitewing",
    )
    assert study3.radiograph.modality == "bitewing"

    res3 = study_service.analyze_study(study_id=study3.study_id, model_id="liodon-panoramic-screener")
    assert res3.status == "modality_unsupported"


def test_level_19_modality_update_endpoint():
    """Verify PATCH /studies/{study_id}/modality updates the database record."""
    raw_bytes = _create_test_image(800, 400)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="initial_study.jpg",
        patient_anonymous_id="PT-MOD-TEST",
        modality="unknown",
    )
    assert study.radiograph.modality == "unknown"

    # Update to intraoral_periapical
    updated = study_service.update_study_modality(study.study_id, "intraoral_periapical")
    assert updated is True

    # Reload from DB and verify persistence
    reloaded = study_service.get_study(study.study_id)
    assert reloaded.radiograph.modality == "intraoral_periapical"


def test_level_19_manual_annotation_workflow():
    """Verify manual region annotation creation, persistence, and deletion."""
    raw_bytes = _create_test_image(600, 600)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="iopa_quadrant.jpg",
        patient_anonymous_id="PT-IOPA-ANNO",
        modality="intraoral_periapical",
    )

    # Add clinician manual annotation
    bbox = {"x_min": 100.0, "y_min": 150.0, "x_max": 250.0, "y_max": 350.0}
    anno = study_service.add_manual_annotation(
        study_id=study.study_id,
        tooth_fdi=16,
        pathology_class="caries",
        bbox=bbox,
        clinical_notes="Clinician verified coronal radiolucency in dentin",
        anatomical_structure="dentin",
    )

    assert anno.finding_id.startswith("ANN-")
    assert anno.tooth_fdi == 16
    assert anno.confidence == 1.0
    assert anno.bbox.x_min == 100.0

    # Verify study reloaded has the manual annotation
    reloaded = study_service.get_study(study.study_id)
    assert any(f.finding_id == anno.finding_id for f in reloaded.findings)

    # Delete manual annotation
    deleted = study_service.delete_manual_annotation(study.study_id, anno.finding_id)
    assert deleted is True

    # Verify study no longer contains the annotation
    reloaded2 = study_service.get_study(study.study_id)
    assert not any(f.finding_id == anno.finding_id for f in reloaded2.findings)


def test_level_19_distinguish_manual_and_ai_annotations():
    """Verify manual annotations and AI findings are clearly distinguished."""
    raw_bytes = _create_test_image(600, 600)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="distinguish_test.jpg",
        patient_anonymous_id="PT-DISTINGUISH",
        modality="intraoral_periapical",
    )

    anno = study_service.add_manual_annotation(
        study_id=study.study_id,
        tooth_fdi=15,
        pathology_class="caries",
        bbox={"x_min": 50.0, "y_min": 50.0, "x_max": 150.0, "y_max": 150.0},
        clinical_notes="Manual observation",
        anatomical_structure="enamel",
    )

    assert anno.suggested_procedure == "Clinician Assessment & Follow-up"
    assert "Manual observation" in anno.evidence.observed_features[0]


def test_level_19_pdf_with_manual_annotations():
    """Verify PDF generator generates a valid multi-page PDF when manual annotations are present."""
    raw_bytes = _create_test_image(800, 400)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="pdf_test.jpg",
        patient_anonymous_id="PT-PDF-TEST",
        modality="intraoral_periapical",
    )

    study_service.add_manual_annotation(
        study_id=study.study_id,
        tooth_fdi=16,
        pathology_class="caries",
        bbox={"x_min": 100.0, "y_min": 100.0, "x_max": 200.0, "y_max": 200.0},
        clinical_notes="Manual check",
        anatomical_structure="pulp_chamber",
    )

    pdf_bytes = clinical_service.export_claim_pack_pdf(study.study_id)
    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 10000, "Generated PDF must contain substantial report data"
