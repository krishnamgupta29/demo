"""Unit tests for CDT code mapping audit across pathologies and anatomical tooth types."""

import pytest
from backend.schemas.finding import PathologyClass
from backend.clinical.cdt_coding import CDTCodingService, DEMO_CDT_CATALOG


def test_periapical_lesion_maps_to_endodontics_by_tooth_type():
    """Periapical lesions must map to endodontic therapy codes D3310 (anterior), D3320 (premolar), D3330 (molar), not D7240."""
    # Anterior (e.g., FDI 11, 21, 31, 41, 12, 22, 13, etc.)
    anterior_candidates = CDTCodingService.suggest_candidate_codes(PathologyClass.PERIAPICAL_LESION, tooth_fdi=11)
    anterior_codes = [c.cdt_code for c in anterior_candidates]
    assert "D3310" in anterior_codes
    assert "D7240" not in anterior_codes  # D7240 is bony impaction, strictly forbidden for periapical lesion

    # Premolar (e.g., FDI 14, 15, 24, 25, 34, 35, 44, 45)
    premolar_candidates = CDTCodingService.suggest_candidate_codes(PathologyClass.PERIAPICAL_LESION, tooth_fdi=14)
    premolar_codes = [c.cdt_code for c in premolar_candidates]
    assert "D3320" in premolar_codes
    assert "D7240" not in premolar_codes

    # Molar (e.g., FDI 16, 26, 36, 46, 47)
    molar_candidates = CDTCodingService.suggest_candidate_codes(PathologyClass.PERIAPICAL_LESION, tooth_fdi=46)
    molar_codes = [c.cdt_code for c in molar_candidates]
    assert "D3330" in molar_codes
    assert "D7240" not in molar_codes


def test_deep_caries_maps_to_endodontics_or_restoration():
    """Deep caries approaching pulp suggests endodontics according to tooth position."""
    # Anterior deep caries -> D3310
    ant_codes = [c.cdt_code for c in CDTCodingService.suggest_candidate_codes(PathologyClass.DEEP_CARIES, tooth_fdi=21, is_deep=True)]
    assert "D3310" in ant_codes
    assert "D2330" in ant_codes

    # Premolar deep caries -> D3320
    pm_codes = [c.cdt_code for c in CDTCodingService.suggest_candidate_codes(PathologyClass.DEEP_CARIES, tooth_fdi=24, is_deep=True)]
    assert "D3320" in pm_codes

    # Molar deep caries -> D3330
    mol_codes = [c.cdt_code for c in CDTCodingService.suggest_candidate_codes(PathologyClass.DEEP_CARIES, tooth_fdi=36, is_deep=True)]
    assert "D3330" in mol_codes


def test_caries_maps_to_appropriate_restorations():
    """Caries maps to anterior resin (D2330) or posterior resin/amalgam (D2391, D2392)."""
    # Anterior caries
    ant_codes = [c.cdt_code for c in CDTCodingService.suggest_candidate_codes(PathologyClass.CARIES, tooth_fdi=12)]
    assert "D2330" in ant_codes
    assert "D2391" not in ant_codes  # D2391 is posterior

    # Posterior caries (premolar/molar)
    post_codes = [c.cdt_code for c in CDTCodingService.suggest_candidate_codes(PathologyClass.CARIES, tooth_fdi=46)]
    assert "D2391" in post_codes
    assert "D2330" not in post_codes


def test_impacted_tooth_maps_to_surgical_extraction():
    """Impacted teeth map to surgical extraction codes D7230/D7240, never conservative restorations or endodontics."""
    imp_codes = [c.cdt_code for c in CDTCodingService.suggest_candidate_codes(PathologyClass.IMPACTED_TOOTH, tooth_fdi=48)]
    assert "D7230" in imp_codes
    assert "D7240" in imp_codes
    assert "D2140" not in imp_codes
    assert "D3330" not in imp_codes


def test_cdt_code_consistency_validation_rules():
    """Validates anatomical constraints: D3310 for anterior, D3320 for premolar, D3330 for molar."""
    # D3310 valid for anterior 11, invalid for molar 16
    v1, e1 = CDTCodingService.validate_code_consistency("D3310", "Anterior Endodontic Therapy", 11)
    assert v1 is True
    v2, e2 = CDTCodingService.validate_code_consistency("D3310", "Anterior Endodontic Therapy", 16)
    assert v2 is False
    assert "anterior teeth" in e2.lower()

    # D3320 valid for premolar 25, invalid for anterior 21
    v3, e3 = CDTCodingService.validate_code_consistency("D3320", "Premolar Endodontics", 25)
    assert v3 is True
    v4, e4 = CDTCodingService.validate_code_consistency("D3320", "Premolar Endodontics", 21)
    assert v4 is False
    assert "premolar teeth" in e4.lower()

    # D3330 valid for molar 46, invalid for premolar 44
    v5, e5 = CDTCodingService.validate_code_consistency("D3330", "Molar Endodontics", 46)
    assert v5 is True
    v6, e6 = CDTCodingService.validate_code_consistency("D3330", "Molar Endodontics", 44)
    assert v6 is False
    assert "molar teeth" in e6.lower()

    # D7240 requires surgical impaction description
    v7, e7 = CDTCodingService.validate_code_consistency("D7240", "Routine Cleaning", 38)
    assert v7 is False
    assert "impaction surgery" in e7.lower()
