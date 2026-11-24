"""Tests for IOPA (Intraoral Periapical) AI workflow and modality gating."""

from pathlib import Path
from PIL import Image
import io
import pytest
from backend.services.study_service import study_service
from backend.schemas.study import StudyStatus


def _create_periapical_image(width=800, height=600) -> bytes:
    img = Image.new("L", (width, height), color=128)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_iopa_study_creation_and_modality():
    raw_bytes = _create_periapical_image(800, 600)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="iopa_test.jpg",
        patient_anonymous_id="PT-IOPA-01",
        modality="intraoral_periapical",
    )
    assert study.radiograph.modality == "intraoral_periapical"


def test_iopa_blocks_panoramic_models_safety_guard():
    raw_bytes = _create_periapical_image(800, 600)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="iopa_safety.jpg",
        patient_anonymous_id="PT-IOPA-02",
        modality="intraoral_periapical",
    )
    res = study_service.analyze_study(
        study_id=study.study_id,
        model_id="liodon-panoramic-screener",
    )
    assert res.status == "modality_unsupported"
    assert "MODALITY_SAFETY_GUARD" in (res.notice or "")


def test_iopa_periapical_screener_execution():
    raw_bytes = _create_periapical_image(800, 600)
    study = study_service.create_study(
        raw_bytes=raw_bytes,
        original_filename="iopa_exec.jpg",
        patient_anonymous_id="PT-IOPA-03",
        modality="intraoral_periapical",
    )
    res = study_service.analyze_study(
        study_id=study.study_id,
        model_id="iopa-periapical-screener",
        conf_threshold=0.25,
    )
    assert res.status == "completed"
    assert res.model_id == "iopa-periapical-screener"
    assert isinstance(res.findings, list)

    reloaded = study_service.get_study(study.study_id)
    assert reloaded.status == StudyStatus.ANALYZED
