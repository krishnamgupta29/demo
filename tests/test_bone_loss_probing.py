"""Unit tests for alveolar bone loss and clinician probing depth path (TASK F4)."""

import pytest
from backend.schemas.finding import PathologyClass
from backend.clinical.cdt_coding import CDTCodingService


def test_d4341_suppressed_when_no_probing_depth():
    """D4341 must NOT be suggested from automated AI finding alone without clinician probing depth."""
    codes_none = CDTCodingService.suggest_candidate_codes(
        pathology=PathologyClass.ALVEOLAR_BONE_LOSS,
        tooth_fdi=46,
        probing_depth_mm=None,
    )
    assert len(codes_none) == 0, f"Expected no code suggestions, got: {[c.cdt_code for c in codes_none]}"

    codes_shallow = CDTCodingService.suggest_candidate_codes(
        pathology=PathologyClass.ALVEOLAR_BONE_LOSS,
        tooth_fdi=46,
        probing_depth_mm=2.5,  # Physiological / non-pathologic depth (< 4.0 mm)
    )
    assert len(codes_shallow) == 0, f"Expected no code suggestions for shallow probing, got: {[c.cdt_code for c in codes_shallow]}"


def test_d4341_suggested_only_when_clinician_probing_depth_exists():
    """D4341 must be suggested when objective clinician-entered probing depth >= 4.0 mm exists."""
    codes_deep = CDTCodingService.suggest_candidate_codes(
        pathology=PathologyClass.ALVEOLAR_BONE_LOSS,
        tooth_fdi=46,
        probing_depth_mm=5.5,
    )
    assert len(codes_deep) == 1
    assert codes_deep[0].cdt_code == "D4341"
    assert "periodontal" in codes_deep[0].display_name.lower()
