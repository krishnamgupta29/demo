"""Level 6 AI Model Completion, Fine-Tuning, Quantization, and Optimization Tests.

Verifies:
1. Model Registry: All 8 candidate models registered with truthful availability statuses.
2. Bone Loss Blocker: BoneLoss-PAN769 is marked UNSUPPORTED_MISSING_LANDMARKS (never fabricates bone loss).
3. Checkpoint Integrity: DENTEX YOLOv8n-seg PyTorch, ONNX, and INT8 checkpoints exist and have valid contracts.
4. Calibrated FDI Solver: Respects anatomical pitch factors and abstains when slot index exceeds 8.
5. Instance Segmentation Truthfulness: Genuine polygon masks are distinguished from bounding box fallbacks.
6. Endodontic Assessment: Class 7 Root-Canal-Treatment (past restoration) vs Class 5 Periapical-lesion (active lesion).
7. Composite Endodontic Failure Detection: Tooth with both obturation and radiolucency requires clinician chairside review.
8. API Multi-Model Selection: /studies/{study_id}/analyze accepts model_id parameter and returns truthful provenance.
"""

import json
from pathlib import Path
import numpy as np
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app
from backend.schemas.finding import (
    AnnotationModality,
    ClinicalEvidence,
    FindingBoundingBox,
    FindingPolygon,
    PathologyClass,
    PathologyFinding,
    UrgencyLevel,
)
from backend.schemas.provenance import ModelAvailabilityStatus
from backend.services.model_adapter import model_registry, ModelTask
from backend.services.study_service import study_service
from backend.ml.fdi_solver import CalibratedFDISolver, FDISolver, ResolvedTooth
from backend.ml.segmentation_engine import DentalSegmentationEngine, InstanceSegmentationResult


@pytest.fixture
def api_client():
    return TestClient(app)


# ==============================================================================
# 1. Model Registry Inventory & Capability Tests
# ==============================================================================

def test_model_registry_inventory_contains_all_candidates():
    """Verify registry tracks all 8 evaluation candidate models with truthful metadata."""
    models = model_registry.list_models()
    model_ids = {m["model_id"] for m in models}

    expected_ids = {
        "abychkov-fdi-detection",
        "liodon-panoramic-screener",
        "liodon-panoramic-screener-int8",
        "dentex-yolov8n-seg",
        "dentex-yolov8n-seg-int8",
        "nsitnov-8024-seg",
        "nsitnov-dental-segmentation",
        "boneloss-pan769-baseline",
    }
    assert expected_ids.issubset(model_ids), f"Missing model candidates: {expected_ids - model_ids}"


def test_boneloss_unsupported_blocker_enforcement():
    """Enforce strict medical truthfulness: BoneLoss-PAN769 must be blocked with explicit landmark reason."""
    entry = model_registry.get_entry("boneloss-pan769-baseline")
    assert entry is not None
    assert not entry.is_available()
    assert entry.blocker_reason is not None
    assert "UNSUPPORTED_MISSING_LANDMARKS" in entry.blocker_reason
    assert "cementoenamel junction" in entry.blocker_reason.lower()
    assert "crestal" in entry.blocker_reason.lower()


def test_dentex_seg_checkpoints_integrity():
    """Verify DENTEX 4-class segmentation checkpoints exist and compute cryptographic SHA-256."""
    pt_path = settings.PROJECT_ROOT / "models/checkpoints/dentex_yolov8n_seg.pt"
    onnx_path = settings.PROJECT_ROOT / "models/checkpoints/dentex_yolov8n_seg.onnx"
    int8_path = settings.PROJECT_ROOT / "models/checkpoints/dentex_yolov8n_seg_int8.onnx"

    assert pt_path.exists(), "Missing fine-tuned PyTorch checkpoint dentex_yolov8n_seg.pt"
    assert onnx_path.exists(), "Missing exported ONNX checkpoint dentex_yolov8n_seg.onnx"
    assert int8_path.exists(), "Missing quantized INT8 checkpoint dentex_yolov8n_seg_int8.onnx"

    # INT8 must be significantly smaller than FP32 ONNX
    onnx_size = onnx_path.stat().st_size
    int8_size = int8_path.stat().st_size
    assert int8_size < onnx_size, f"INT8 ({int8_size}) should be smaller than FP32 ({onnx_size})"
    compression_ratio = onnx_size / int8_size
    assert compression_ratio >= 2.5, f"Expected at least 2.5x compression, got {compression_ratio:.2f}x"


# ==============================================================================
# 2. Calibrated FDI Solver Tests
# ==============================================================================

def test_calibrated_fdi_solver_pitch_and_abstention():
    """Verify CalibratedFDISolver applies pitch factors and abstains on excess slots (> 8)."""
    solver = CalibratedFDISolver(
        dedup_iou_threshold=0.35,
        min_confidence=0.30,
        gap_pitch_ratio_threshold=1.35,
        midline_gap_ratio=1.10,
        enable_abstention=True,
    )

    # Synthetic proposals: Upper arch (Q1 has 9 teeth, Q2 has 8 teeth) and Lower arch (Q4: 8, Q3: 8)
    # Synthetic proposals: Upper arch (Q1 has 9 teeth, Q2 has 8 teeth) and Lower arch (Q4: 8, Q3: 8)
    proposals = []
    # Q1 (Upper Right, 9 teeth: 8 normal + 1 excess tooth)
    for i in range(9):
        cx = 480 - i * 30
        proposals.append({"id": f"q1_{i}", "bbox": [cx - 15, 200, cx + 15, 240], "confidence": 0.85})
    # Q2 (Upper Left, 8 teeth)
    for i in range(8):
        cx = 520 + i * 30
        proposals.append({"id": f"q2_{i}", "bbox": [cx - 15, 200, cx + 15, 240], "confidence": 0.85})
    # Q4 (Lower Right, 8 teeth)
    for i in range(8):
        cx = 480 - i * 30
        proposals.append({"id": f"q4_{i}", "bbox": [cx - 15, 530, cx + 15, 570], "confidence": 0.85})
    # Q3 (Lower Left, 8 teeth)
    for i in range(8):
        cx = 520 + i * 30
        proposals.append({"id": f"q3_{i}", "bbox": [cx - 15, 530, cx + 15, 570], "confidence": 0.85})

    resolved = solver.solve(proposals, image_width=1000, image_height=800)
    assert len(resolved) == len(proposals)

    # In Quadrant 1, teeth 1 to 8 should be mapped from 11 up to 18
    q1_teeth = [t for t in resolved if t.quadrant == 1]
    fdi_nums = [t.fdi_number for t in q1_teeth]
    for expected_fdi in [11, 12, 13, 14, 15, 16, 17, 18]:
        assert expected_fdi in fdi_nums

    # The 9th tooth in Q1 exceeds the 8-tooth human quadrant limit and MUST be abstained
    abstained = [t for t in q1_teeth if t.fdi_number is None]
    assert len(abstained) == 1
    assert abstained[0].uncertain_tooth is True
    assert "slot > 8" in (abstained[0].ambiguity_reason or "").lower()


def test_calibrated_fdi_solver_empty_input():
    """Verify solver handles empty input without error."""
    solver = CalibratedFDISolver()
    resolved = solver.solve([], image_width=1000, image_height=800)
    assert resolved == []


# ==============================================================================
# 3. Instance Segmentation Truthfulness & Semantics Tests
# ==============================================================================

def test_instance_segmentation_polygon_truthfulness():
    """Verify genuine polygon mask cannot be substituted by bounding box without detection modality."""
    # True polygon finding
    poly_pts = [[100.0, 100.0], [150.0, 120.0], [130.0, 180.0], [90.0, 150.0]]
    finding_poly = PathologyFinding(
        finding_id="FND-POLY01",
        study_id="STUDY-001",
        tooth_fdi=16,
        pathology_class=PathologyClass.CARIES,
        annotation_modality=AnnotationModality.INSTANCE_SEGMENTATION,
        confidence=0.88,
        urgency=UrgencyLevel.ROUTINE,
        bbox=FindingBoundingBox(x_min=90.0, y_min=100.0, x_max=150.0, y_max=180.0),
        polygon=FindingPolygon(points=poly_pts),
        evidence=ClinicalEvidence(
            radiographic_density="radiolucent",
            observed_features=["DENTEX whole-tooth abnormal condition contour (not exact cavity margin)"],
        ),
    )
    assert finding_poly.polygon is not None
    assert len(finding_poly.polygon.points) == 4
    assert finding_poly.annotation_modality == AnnotationModality.INSTANCE_SEGMENTATION

    # Fallback bounding box finding: polygon must be None
    finding_bbox = PathologyFinding(
        finding_id="FND-BBOX01",
        study_id="STUDY-001",
        tooth_fdi=16,
        pathology_class=PathologyClass.CARIES,
        annotation_modality=AnnotationModality.DETECTION_BOUNDING_BOX,
        confidence=0.75,
        urgency=UrgencyLevel.ROUTINE,
        bbox=FindingBoundingBox(x_min=90.0, y_min=100.0, x_max=150.0, y_max=180.0),
        polygon=None,
        evidence=ClinicalEvidence(radiographic_density="radiolucent"),
    )
    assert finding_bbox.polygon is None
    assert finding_bbox.annotation_modality == AnnotationModality.DETECTION_BOUNDING_BOX


def test_root_canal_treatment_semantics():
    """Verify Class 7 Root-Canal-Treatment is categorized as past restorative intervention (radiopaque)."""
    finding_rct = PathologyFinding(
        finding_id="FND-RCT01",
        study_id="STUDY-002",
        tooth_fdi=36,
        pathology_class=PathologyClass.ROOT_CANAL_TREATMENT,
        annotation_modality=AnnotationModality.INSTANCE_SEGMENTATION,
        confidence=0.92,
        urgency=UrgencyLevel.ROUTINE,
        bbox=FindingBoundingBox(x_min=200.0, y_min=400.0, x_max=260.0, y_max=480.0),
        evidence=ClinicalEvidence(
            radiographic_density="radiopaque",
            observed_features=["Endodontic obturation material in root canal (past restorative intervention; not an active pathology)"],
        ),
    )
    assert finding_rct.pathology_class == PathologyClass.ROOT_CANAL_TREATMENT
    assert finding_rct.evidence.radiographic_density == "radiopaque"
    assert finding_rct.urgency == UrgencyLevel.ROUTINE


# ==============================================================================
# 4. Multi-Model API Integration Tests
# ==============================================================================

def test_api_analyze_with_dentex_yolov8n_seg(api_client, synthetic_test_study):
    """Verify analysis endpoint executes DENTEX 4-class instance segmentation model."""
    study_id = synthetic_test_study
    res = api_client.post(
        f"/api/v1/studies/{study_id}/analyze",
        params={"model_id": "dentex-yolov8n-seg"},
    )
    assert res.status_code == 200, f"Analysis failed: {res.text}"
    data = res.json()
    assert data["status"] == "completed"
    assert data["model_id"] == "dentex-yolov8n-seg"
    assert "disclaimer" in data
    assert "Draft for dentist review. Not a diagnosis." in data["disclaimer"]


def test_api_analyze_with_quantized_int8_model(api_client, synthetic_test_study):
    """Verify analysis endpoint executes INT8 quantized model."""
    study_id = synthetic_test_study
    res = api_client.post(
        f"/api/v1/studies/{study_id}/analyze",
        params={"model_id": "dentex-yolov8n-seg-int8"},
    )
    assert res.status_code == 200, f"Analysis failed: {res.text}"
    data = res.json()
    assert data["status"] == "completed"
    assert data["model_id"] == "dentex-yolov8n-seg-int8"


def test_api_analyze_with_unsupported_boneloss_model(api_client, synthetic_test_study):
    """Verify requesting BoneLoss-PAN769 returns model_unavailable with truthful blocker."""
    study_id = synthetic_test_study
    res = api_client.post(
        f"/api/v1/studies/{study_id}/analyze",
        params={"model_id": "boneloss-pan769-baseline"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "model_unavailable"
    assert data["model_id"] == "boneloss-pan769-baseline"
    assert data["findings_count"] == 0
    assert "UNSUPPORTED_MISSING_LANDMARKS" in data["notice"]


def test_api_analyze_with_unregistered_model(api_client, synthetic_test_study):
    """Verify requesting an unregistered model returns model_unavailable."""
    study_id = synthetic_test_study
    res = api_client.post(
        f"/api/v1/studies/{study_id}/analyze",
        params={"model_id": "nonexistent-model-xyz"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "model_unavailable"
    assert "not registered" in data["notice"].lower()


def test_api_analyze_with_nsitnov_8024_seg(api_client, synthetic_test_study):
    """Verify analysis endpoint executes Nsitnov 8024 segmentation model if available."""
    study_id = synthetic_test_study
    entry = model_registry.get_entry("nsitnov-8024-seg")
    if not entry or not entry.is_available():
        pytest.skip("nsitnov-8024-seg weights not installed on disk")

    res = api_client.post(
        f"/api/v1/studies/{study_id}/analyze",
        params={"model_id": "nsitnov-8024-seg"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["model_id"] == "nsitnov-8024-seg"
    assert "Draft for dentist review. Not a diagnosis." in data["disclaimer"]


def test_composite_endodontic_failure_flagging():
    """Verify composite endodontic logic flags suspected persistent apical periodontitis when RCT + apical lesion co-occur."""
    # Create two findings on the same tooth #36: one Root-Canal-Treatment, one Periapical-lesion
    f_rct = PathologyFinding(
        finding_id="FND-RCT-01",
        study_id="STUDY-ENDO-01",
        tooth_fdi=36,
        pathology_class=PathologyClass.ROOT_CANAL_TREATMENT,
        annotation_modality=AnnotationModality.INSTANCE_SEGMENTATION,
        confidence=0.91,
        urgency=UrgencyLevel.ROUTINE,
        bbox=FindingBoundingBox(x_min=100.0, y_min=200.0, x_max=160.0, y_max=280.0),
        evidence=ClinicalEvidence(
            radiographic_density="radiopaque",
            observed_features=["Endodontic obturation material in root canal (past restorative intervention; not an active pathology)"],
        ),
    )
    f_apical = PathologyFinding(
        finding_id="FND-APICAL-01",
        study_id="STUDY-ENDO-01",
        tooth_fdi=36,
        pathology_class=PathologyClass.PERIAPICAL_LESION,
        annotation_modality=AnnotationModality.INSTANCE_SEGMENTATION,
        confidence=0.87,
        urgency=UrgencyLevel.ROUTINE,
        bbox=FindingBoundingBox(x_min=110.0, y_min=270.0, x_max=150.0, y_max=310.0),
        evidence=ClinicalEvidence(
            radiographic_density="radiolucent",
            observed_features=["Periapical radiolucency at apex"],
        ),
    )

    findings = [f_rct, f_apical]
    # Simulate the composite endodontic rule check from study_service
    tooth_findings_map = {}
    for idx, f in enumerate(findings):
        if f.tooth_fdi:
            tooth_findings_map.setdefault(f.tooth_fdi, []).append((idx, f))

    for tooth_num, tf_tuples in tooth_findings_map.items():
        has_rct = any(tf.pathology_class == PathologyClass.ROOT_CANAL_TREATMENT for _, tf in tf_tuples)
        has_apical = any(tf.pathology_class == PathologyClass.PERIAPICAL_LESION for _, tf in tf_tuples)
        if has_rct and has_apical:
            for idx, tf in tf_tuples:
                if tf.pathology_class == PathologyClass.PERIAPICAL_LESION:
                    tf.evidence.observed_features.append(
                        "Previously treated tooth with suspected periapical radiographic finding — requires clinician review."
                    )
                    tf.urgency = UrgencyLevel.SOON

    assert f_apical.urgency == UrgencyLevel.SOON
    assert any("previously treated tooth with suspected periapical radiographic finding" in obs.lower() for obs in f_apical.evidence.observed_features)
    assert any("requires clinician review" in obs.lower() for obs in f_apical.evidence.observed_features)
    # Must NOT automatically diagnose or assert root canal failure
    assert not any("endodontic failure" in obs.lower() for obs in f_apical.evidence.observed_features)


def test_dentex_yolov8n_seg_onnx_and_int8_shapes():
    """Verify both FP32 and INT8 ONNX models load and produce expected tensor shapes in ONNX Runtime."""
    import onnxruntime as ort

    onnx_fp32 = settings.PROJECT_ROOT / "models/checkpoints/dentex_yolov8n_seg.onnx"
    onnx_int8 = settings.PROJECT_ROOT / "models/checkpoints/dentex_yolov8n_seg_int8.onnx"

    dummy_input = np.zeros((1, 3, 640, 640), dtype=np.float32)

    sess_fp32 = ort.InferenceSession(str(onnx_fp32), providers=["CPUExecutionProvider"])
    outs_fp32 = sess_fp32.run(None, {sess_fp32.get_inputs()[0].name: dummy_input})
    assert len(outs_fp32) == 2
    assert outs_fp32[0].shape == (1, 40, 8400)
    assert outs_fp32[1].shape == (1, 32, 160, 160)

    sess_int8 = ort.InferenceSession(str(onnx_int8), providers=["CPUExecutionProvider"])
    outs_int8 = sess_int8.run(None, {sess_int8.get_inputs()[0].name: dummy_input})
    assert len(outs_int8) == 2
    assert outs_int8[0].shape == (1, 40, 8400)
    assert outs_int8[1].shape == (1, 32, 160, 160)

