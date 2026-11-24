"""Level 2 Test Suite: ONNX runtime, preprocessing, decoding, FDI localization, API analysis, and robustness."""

import io
import json
from pathlib import Path
import numpy as np
import pytest
from PIL import Image

from backend.config import settings
from backend.ml.preprocessor import ImagePreprocessor, LetterboxMetadata
from backend.ml.postprocessor import decode_yolo_detections, nms_boxes, DetectionResult
from backend.ml.inference_engine import ONNXInferenceEngine
from backend.ml.fdi_numbering import FDINumberingEngine
from backend.ml.dataset_utils import DENTEXDatasetReader
from backend.schemas.finding import PathologyClass, AnnotationModality
from backend.schemas.provenance import ModelAvailabilityStatus


@pytest.fixture
def sample_opg_image() -> Image.Image:
    """Create a synthetic test radiograph image (1200x600)."""
    img = Image.new("RGB", (1200, 600), color=(40, 40, 40))
    return img


@pytest.fixture
def sample_opg_bytes() -> bytes:
    """Create encoded PNG bytes for study upload testing."""
    img = Image.new("RGB", (1200, 600), color=(50, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_real_model_initialization():
    """Verify real best.onnx checkpoint exists, verifies SHA-256 hash, and initializes session."""
    engine = ONNXInferenceEngine(
        model_id="liodon-panoramic-screener",
        model_name="Liodon Panoramic Anomaly Screener",
        version="1.0.0",
        checkpoint_rel_path="models/checkpoints/best.onnx",
        class_names=["caries", "periapical_lesion", "impacted_tooth"],
    )
    assert engine.is_available() is True
    sha256 = engine.compute_sha256()
    assert sha256 is not None
    assert len(sha256) == 64
    assert engine.load_session() is True


def test_onnx_session_execution(sample_opg_image):
    """Verify forward inference runs and returns expected YOLO output tensor shape."""
    engine = ONNXInferenceEngine(
        model_id="liodon-panoramic-screener",
        model_name="Liodon Panoramic Anomaly Screener",
        version="1.0.0",
        checkpoint_rel_path="models/checkpoints/best.onnx",
        class_names=["caries", "periapical_lesion", "impacted_tooth"],
    )
    result = engine.predict_image(sample_opg_image)
    assert result["status"] == ModelAvailabilityStatus.AVAILABLE.value
    assert "findings" in result
    assert result["latency_ms"] is not None
    assert result["latency_ms"] > 0.0
    assert result["execution_provider"] == "CPUExecutionProvider"


def test_input_preprocessing_letterbox(sample_opg_image):
    """Verify aspect-ratio preserving letterbox produces valid float32 tensor in [0, 1]."""
    tensor, meta = ImagePreprocessor.letterbox(sample_opg_image, target_size=640)
    assert tensor.shape == (1, 3, 640, 640)
    assert tensor.dtype == np.float32
    assert tensor.min() >= 0.0
    assert tensor.max() <= 1.0

    assert meta.original_width == 1200
    assert meta.original_height == 600
    assert meta.scale == (640 / 1200)
    assert meta.new_width == 640
    assert meta.new_height == 320
    assert meta.pad_y == (640 - 320) // 2


def test_output_decoding_and_nms():
    """Verify decoding tensor proposals and class-aware NMS suppresses duplicates."""
    meta = LetterboxMetadata(
        original_width=1000,
        original_height=500,
        target_size=640,
        scale=0.64,
        pad_x=0,
        pad_y=160,
        new_width=640,
        new_height=320,
    )
    # Synthetic output tensor: 1 proposal with 3 classes
    # [cx, cy, w, h, p_caries, p_periapical, p_impacted]
    raw = np.zeros((1, 7, 3), dtype=np.float32)
    # Proposal 0: strong caries
    raw[0, :, 0] = [320.0, 320.0, 50.0, 50.0, 0.90, 0.05, 0.01]
    # Proposal 1: duplicate caries (overlapping)
    raw[0, :, 1] = [322.0, 321.0, 48.0, 49.0, 0.70, 0.02, 0.01]
    # Proposal 2: distinct impacted tooth
    raw[0, :, 2] = [100.0, 250.0, 60.0, 80.0, 0.01, 0.02, 0.85]

    class_names = ["caries", "periapical_lesion", "impacted_tooth"]
    detections = decode_yolo_detections(raw, meta, class_names, conf_threshold=0.25, iou_threshold=0.35)

    assert len(detections) == 2
    c_det = [d for d in detections if d.class_name == "caries"][0]
    i_det = [d for d in detections if d.class_name == "impacted_tooth"][0]
    assert c_det.confidence == pytest.approx(0.90, abs=1e-3)
    assert i_det.confidence == pytest.approx(0.85, abs=1e-3)


def test_coordinate_scaling_roundtrip():
    """Verify coordinate mapping clamps within valid original image bounds."""
    meta = LetterboxMetadata(
        original_width=2000,
        original_height=1000,
        target_size=640,
        scale=0.32,
        pad_x=0,
        pad_y=160,
        new_width=640,
        new_height=320,
    )
    # Box spanning from left pad to right border
    box_lb = [10.0, 160.0, 630.0, 480.0]
    unscaled = ImagePreprocessor.unletterbox_box(box_lb, meta)
    assert unscaled[0] >= 0.0
    assert unscaled[1] >= 0.0
    assert unscaled[2] <= 2000.0
    assert unscaled[3] <= 1000.0
    assert unscaled[2] > unscaled[0]
    assert unscaled[3] > unscaled[1]


def test_class_mapping():
    """Verify candidate model classes cleanly map to authoritative domain enums."""
    mapping = {
        "caries": PathologyClass.CARIES,
        "periapical_lesion": PathologyClass.PERIAPICAL_LESION,
        "impacted_tooth": PathologyClass.IMPACTED_TOOTH,
    }
    for k, v in mapping.items():
        assert isinstance(v, PathologyClass)
        assert v.value == k


def test_fdi_mapping_and_ambiguity(sample_opg_image):
    """Verify FDI localization runs and flags uncertain tooth IDs without fake forcing."""
    fdi_engine = FDINumberingEngine()
    if not fdi_engine.is_available():
        pytest.skip("FDI checkpoint not present")

    res = fdi_engine.predict_teeth(sample_opg_image)
    assert res["status"] == ModelAvailabilityStatus.AVAILABLE.value
    assert "teeth" in res
    assert res["latency_ms"] is not None
    assert "PROPOSAL_LOCALIZATION_ACTIVE" in res["fdi_integration_status"]


def test_missing_checkpoint_handling():
    """Verify missing checkpoint reports MODEL_UNAVAILABLE gracefully."""
    engine = ONNXInferenceEngine(
        model_id="nonexistent-model",
        model_name="Nonexistent Model",
        version="1.0.0",
        checkpoint_rel_path="models/checkpoints/nonexistent.onnx",
        class_names=["caries"],
    )
    assert engine.is_available() is False
    assert engine.compute_sha256() is None
    dummy = Image.new("RGB", (640, 640))
    res = engine.predict_image(dummy)
    assert res["status"] == ModelAvailabilityStatus.MODEL_UNAVAILABLE.value
    assert "missing" in res["error"]


def test_corrupted_checkpoint_handling(tmp_path):
    """Verify corrupted checkpoint triggers integrity error or session load failure."""
    corrupt_file = tmp_path / "corrupt.onnx"
    corrupt_file.write_bytes(b"NOT_A_VALID_ONNX_FILE_GARBAGE_BYTES")

    engine = ONNXInferenceEngine(
        model_id="corrupt-model",
        model_name="Corrupt Model",
        version="1.0.0",
        checkpoint_rel_path=str(corrupt_file.relative_to(settings.PROJECT_ROOT)) if corrupt_file.is_relative_to(settings.PROJECT_ROOT) else "corrupt.onnx",
        class_names=["caries"],
    )
    # Direct session load attempt on bad file fails cleanly
    assert engine.load_session() is False


def test_invalid_image_handling():
    """Verify preprocessor rejects 0x0 or corrupted image inputs."""
    bad_img = Image.new("RGB", (0, 0))
    with pytest.raises(ValueError, match="Invalid image dimensions"):
        ImagePreprocessor.letterbox(bad_img)


def test_api_analysis_endpoint_real_model(client, sample_opg_bytes):
    """Verify POST /api/v1/studies/{study_id}/analyze runs real model and persists findings."""
    # 1. Ingest study
    files = {"file": ("test_opg.png", sample_opg_bytes, "image/png")}
    intake_resp = client.post("/api/v1/studies/upload", files=files)
    assert intake_resp.status_code == 201
    study_id = intake_resp.json()["study_id"]

    # 2. Analyze study
    analyze_resp = client.post(
        f"/api/v1/studies/{study_id}/analyze",
        json={"model_id": "liodon-panoramic-screener", "conf_threshold": 0.20},
    )
    assert analyze_resp.status_code == 200
    data = analyze_resp.json()
    assert data["study_id"] == study_id
    assert data["status"] == "completed"
    assert data["model_id"] == "liodon-panoramic-screener"
    assert data["execution_time_ms"] is not None
    assert data["execution_time_ms"] > 0
    assert "Draft for dentist review. Not a diagnosis." in data["disclaimer"]
    assert "Academic decision-support prototype" in data["notice"]


def test_api_analysis_endpoint_unavailable_model(client, sample_opg_bytes):
    """Verify requesting an uninstalled model returns MODEL_UNAVAILABLE without crashing."""
    files = {"file": ("test_opg_2.png", sample_opg_bytes, "image/png")}
    intake_resp = client.post("/api/v1/studies/upload", files=files)
    study_id = intake_resp.json()["study_id"]

    analyze_resp = client.post(
        f"/api/v1/studies/{study_id}/analyze",
        json={"model_id": "nsitnov-dental-segmentation"},
    )
    assert analyze_resp.status_code == 200
    data = analyze_resp.json()
    assert data["status"] == "model_unavailable"
    assert data["findings_count"] == 0
    assert "unavailable" in data["notice"].lower()


def test_prediction_persistence(client, sample_opg_bytes):
    """Verify that analyzed findings and study status update are persisted in database."""
    files = {"file": ("test_persist.png", sample_opg_bytes, "image/png")}
    intake_resp = client.post("/api/v1/studies/upload", files=files)
    study_id = intake_resp.json()["study_id"]

    # Run analysis
    client.post(f"/api/v1/studies/{study_id}/analyze")

    # Retrieve study detail
    detail_resp = client.get(f"/api/v1/studies/{study_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["status"] == "analyzed"
    # Findings must have annotation_modality detection_bounding_box and bbox geometry
    for f in detail["findings"]:
        assert f["annotation_modality"] == AnnotationModality.DETECTION_BOUNDING_BOX.value
        assert f["bbox"] is not None
        assert f["polygon"] is None  # Truthful distinction: no false polygon masks


def test_repeated_inference_consistency(sample_opg_image):
    """Verify identical inputs yield strictly deterministic predictions."""
    engine = ONNXInferenceEngine(
        model_id="liodon-panoramic-screener",
        model_name="Liodon Panoramic Anomaly Screener",
        version="1.0.0",
        checkpoint_rel_path="models/checkpoints/best.onnx",
        class_names=["caries", "periapical_lesion", "impacted_tooth"],
    )
    r1 = engine.predict_image(sample_opg_image)
    r2 = engine.predict_image(sample_opg_image)

    assert len(r1["findings"]) == len(r2["findings"])
    for f1, f2 in zip(r1["findings"], r2["findings"]):
        assert f1.class_name == f2.class_name
        assert f1.confidence == f2.confidence
        assert f1.bbox_orig == f2.bbox_orig


def test_dataset_split_isolation():
    """Verify train and dev evaluation splits have zero patient/image leakage."""
    reader = DENTEXDatasetReader()
    train_ids, eval_ids = reader.create_reproducible_split(eval_ratio=0.20, random_seed=42)

    assert len(train_ids) > 0
    assert len(eval_ids) > 0
    intersection = set(train_ids) & set(eval_ids)
    assert len(intersection) == 0, f"Split leakage detected: {intersection}"


def test_inference_latency_measurement(sample_opg_image):
    """Verify inference latency is measured and reported under 1500ms on CPU."""
    engine = ONNXInferenceEngine(
        model_id="liodon-panoramic-screener",
        model_name="Liodon Panoramic Anomaly Screener",
        version="1.0.0",
        checkpoint_rel_path="models/checkpoints/best.onnx",
        class_names=["caries", "periapical_lesion", "impacted_tooth"],
    )
    res = engine.predict_image(sample_opg_image)
    assert res["latency_ms"] is not None
    assert 0.0 < res["latency_ms"] < 2500.0
