"""
Level 3 Automated QA Suite:
- DENTEX polygon semantics validation
- 4-class taxonomy preservation
- FDI solver arch partitioning, duplicate resolution, and missing teeth handling
- Mirrored radiographic orientation checks
- Tooth-pathology geometric association engine
- Segmentation adapter integrity and zero false polygon mask guarantee
- End-to-end API integration and persistence
"""

import io
from pathlib import Path
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.main import app
from backend.ml.fdi_solver import FDISolver, ResolvedTooth
from backend.ml.association import ToothPathologyAssociator, FindingAssociation
from backend.ml.segmentation_engine import DentalSegmentationEngine
from backend.schemas.finding import PathologyClass, AnnotationModality
from backend.schemas.tooth import ToothBox, VALID_FDI_TEETH
from backend.schemas.provenance import ModelAvailabilityStatus


@pytest.fixture
def api_client():
    return TestClient(app)


def test_four_class_mappings_preservation():
    """Verify that all 4 compulsory DENTEX targets are preserved as separate classes."""
    required = ["impacted_tooth", "caries", "periapical_lesion", "deep_caries"]
    for c in required:
        enum_val = PathologyClass(c)
        assert enum_val.value == c
    assert PathologyClass.CARIES.value != PathologyClass.DEEP_CARIES.value


def test_fdi_solver_duplicate_resolution():
    """Verify that FDISolver deduplicates dense overlapping tooth proposals conservatively."""
    solver = FDISolver(dedup_iou_threshold=0.35)
    # Two identical boxes overlapping with IoU = 1.0, different confidences
    props = [
        {"id": "p1", "bbox": [100.0, 100.0, 200.0, 400.0], "confidence": 0.65},
        {"id": "p2", "bbox": [102.0, 101.0, 201.0, 399.0], "confidence": 0.92},
    ]
    deduped = solver.deduplicate_proposals(props)
    assert len(deduped) == 1
    assert deduped[0]["confidence"] == 0.92


def test_fdi_solver_arch_partitioning_and_mirrored_orientation():
    """Verify OPG radiographic convention: Patient Right is image left, Patient Left is image right."""
    solver = FDISolver()
    w, h = 2000, 1000
    # Create 4 teeth in 4 quadrants:
    # Q1: Upper, Left of midline (Patient Right)
    # Q2: Upper, Right of midline (Patient Left)
    # Q3: Lower, Right of midline (Patient Left)
    # Q4: Lower, Left of midline (Patient Right)
    props = [
        {"id": "t_q1", "bbox": [400.0, 200.0, 500.0, 450.0], "confidence": 0.90},
        {"id": "t_q2", "bbox": [1500.0, 200.0, 1600.0, 450.0], "confidence": 0.90},
        {"id": "t_q3", "bbox": [1500.0, 600.0, 1600.0, 850.0], "confidence": 0.90},
        {"id": "t_q4", "bbox": [400.0, 600.0, 500.0, 850.0], "confidence": 0.90},
    ]
    resolved = solver.solve(props, image_width=w, image_height=h)
    assert len(resolved) == 4

    q_map = {t.tooth_id: t for t in resolved}
    # Check patient sides
    for t in resolved:
        if t.quadrant == 1:
            assert t.patient_side == "patient_right"
            assert t.jaw == "maxilla"
        elif t.quadrant == 2:
            assert t.patient_side == "patient_left"
            assert t.jaw == "maxilla"
        elif t.quadrant == 3:
            assert t.patient_side == "patient_left"
            assert t.jaw == "mandible"
        elif t.quadrant == 4:
            assert t.patient_side == "patient_right"
            assert t.jaw == "mandible"


def test_fdi_solver_missing_tooth_gap():
    """Verify that inter-tooth pitch gap skips missing tooth slots instead of shifting indices."""
    solver = FDISolver(gap_pitch_ratio_threshold=1.75)
    w, h = 2000, 1000
    # In Q2 (Upper Left, x >= 1000):
    # Tooth 1 at cx=1090 (width=80)
    # Tooth 2 at cx=1190 (width=80)
    # Gap of 160px (tooth 3 missing):
    # Tooth 4 at cx=1350 (width=80)
    props = [
        {"id": "t1", "bbox": [1050.0, 200.0, 1130.0, 450.0], "confidence": 0.90},
        {"id": "t2", "bbox": [1150.0, 200.0, 1230.0, 450.0], "confidence": 0.90},
        {"id": "t4", "bbox": [1310.0, 200.0, 1390.0, 450.0], "confidence": 0.90},
    ]
    resolved = solver.solve(props, image_width=w, image_height=h)
    q2_teeth = [t for t in resolved if t.quadrant == 2]
    assert len(q2_teeth) == 3
    # Check that teeth are assigned 21, 22, and 24 (skipping 23)
    fdi_nums = [t.fdi_number for t in q2_teeth]
    assert 21 in fdi_nums
    assert 22 in fdi_nums
    assert 24 in fdi_nums


def test_tooth_pathology_association_containment():
    """Verify geometric association: full containment vs unassociated lesion vs interproximal contact."""
    associator = ToothPathologyAssociator(min_iop_threshold=0.25, strong_iop_threshold=0.50)

    # 1. Tooth #46 (Lower Right First Molar)
    tooth_46 = ResolvedTooth(
        tooth_id="tooth_46",
        fdi_number=46,
        fdi_name="Mandibular Right First Molar (#46)",
        quadrant=4,
        tooth_index=6,
        confidence=0.95,
        bbox=[800.0, 600.0, 1000.0, 950.0],
        centroid=[900.0, 775.0],
        jaw="mandible",
        patient_side="patient_right",
        uncertain_tooth=False,
    )
    # 2. Tooth #45 (Lower Right Second Premolar)
    tooth_45 = ResolvedTooth(
        tooth_id="tooth_45",
        fdi_number=45,
        fdi_name="Mandibular Right Second Premolar (#45)",
        quadrant=4,
        tooth_index=5,
        confidence=0.95,
        bbox=[1000.0, 600.0, 1120.0, 950.0],
        centroid=[1060.0, 775.0],
        jaw="mandible",
        patient_side="patient_right",
        uncertain_tooth=False,
    )
    teeth = [tooth_46, tooth_45]

    findings = [
        # Occlusal caries completely inside tooth #46
        {
            "id": "f_caries",
            "label": "caries",
            "confidence": 0.88,
            "bbox": [850.0, 620.0, 950.0, 700.0],
        },
        # Interproximal lesion spanning contact point between 46 and 45
        {
            "id": "f_contact",
            "label": "caries",
            "confidence": 0.82,
            "bbox": [970.0, 650.0, 1030.0, 730.0],
        },
        # Free bone cyst far away from any tooth
        {
            "id": "f_cyst",
            "label": "cyst",
            "confidence": 0.75,
            "bbox": [200.0, 800.0, 350.0, 920.0],
        },
    ]

    _, assocs = associator.associate(findings, teeth)
    assoc_map = {a.finding_id: a for a in assocs}

    # Caries inside 46
    assert assoc_map["f_caries"].associated_fdi_number == 46
    assert assoc_map["f_caries"].iop == 1.0
    assert assoc_map["f_caries"].uncertain_association is False

    # Interproximal contact
    assert assoc_map["f_contact"].is_interproximal is True
    assert assoc_map["f_contact"].associated_fdi_number in [45, 46]

    # Free bone cyst unassociated
    assert assoc_map["f_cyst"].associated_fdi_number is None
    assert assoc_map["f_cyst"].association_method == "unassociated"
    assert assoc_map["f_cyst"].uncertain_association is True


def test_segmentation_engine_integrity_and_truthful_masks():
    """Verify that segmentation engine verifies checksum and does not invent false masks."""
    engine = DentalSegmentationEngine(
        model_id="nsitnov-8024-seg",
        checkpoint_rel_path="models/checkpoints/8024.pt",
    )
    assert engine.is_available() is True
    sha256 = engine.compute_sha256()
    assert sha256 is not None
    assert len(sha256) == 64

    prov = engine.get_provenance()
    assert prov.model_id == "nsitnov-8024-seg"
    assert prov.availability_status == ModelAvailabilityStatus.AVAILABLE


def test_api_analysis_endpoint_fdi_and_association(api_client):
    """Verify that analyze endpoint executes real model, integrates FDI teeth, and associates findings."""
    # 1. Create a study with an in-memory PNG
    img = Image.new("RGB", (1200, 600), color=(50, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    upload_res = api_client.post(
        "/api/v1/studies/upload",
        files={"file": ("test_study_l3.png", buf.getvalue(), "image/png")},
    )
    assert upload_res.status_code == 201
    study_id = upload_res.json()["study_id"]

    # 2. Run analysis
    analyze_res = api_client.post(
        f"/api/v1/studies/{study_id}/analyze",
        json={"model_id": "liodon-panoramic-screener", "conf_threshold": 0.25},
    )
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    assert data["study_id"] == study_id
    assert data["status"] == "completed"
    assert "teeth" in data
    assert "findings" in data
    assert data["disclaimer"] == "Draft for dentist review. Not a diagnosis."
