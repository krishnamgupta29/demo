import pytest
import numpy as np
from backend.schemas.finding import PathologyClass
from backend.schemas.evidence import (
    ClinicalExaminationRecord,
    RadiographicObservation,
    EvidenceSource,
    VerificationStatus,
)
from backend.clinical.attribute_engine import ClinicalAttributeEngine

# 1. Impaction Angulation Tests with Synthetic Masks
def test_impaction_angulation_no_mask():
    res = ClinicalAttributeEngine.classify_impaction_angulation(None, tooth_fdi=48)
    assert res == "angulation not determinable (no mask)"

    res_box = ClinicalAttributeEngine.classify_impaction_angulation([], tooth_fdi=48)
    assert res_box == "angulation not determinable (no mask)"

def test_impaction_angulation_vertical_mask():
    # Elongated vertically: dx small, dy large (e.g. height 100, width 20)
    pts = [
        [100.0, 100.0],
        [120.0, 100.0],
        [120.0, 200.0],
        [100.0, 200.0],
    ]
    res = ClinicalAttributeEngine.classify_impaction_angulation(pts, tooth_fdi=48)
    assert "vertical" in res
    assert "(suspected, requires clinician confirmation)" in res

def test_impaction_angulation_horizontal_mask():
    # Elongated horizontally: dx large, dy small (e.g. width 120, height 20)
    pts = [
        [100.0, 100.0],
        [220.0, 100.0],
        [220.0, 120.0],
        [100.0, 120.0],
    ]
    res = ClinicalAttributeEngine.classify_impaction_angulation(pts, tooth_fdi=48)
    assert "horizontal" in res
    assert "(suspected, requires clinician confirmation)" in res

def test_impaction_angulation_mesioangular_mask():
    # 45-degree angle
    pts = [
        [100.0, 200.0],
        [120.0, 200.0],
        [170.0, 150.0],
        [150.0, 150.0],
    ]
    res = ClinicalAttributeEngine.classify_impaction_angulation(pts, tooth_fdi=48)
    assert "mesioangular" in res
    assert "(suspected, requires clinician confirmation)" in res


# 2. Deep Caries Wording Tests
def test_deep_caries_without_vitality():
    wording = ClinicalAttributeEngine.format_caries_wording(
        pathology_class=PathologyClass.DEEP_CARIES,
        clinical_examinations=[],
        tooth_fdi=36,
    )
    assert wording == "deep caries, radiographically approaching the pulp (suspected)"
    assert "pulp involvement confirmed" not in wording

def test_deep_caries_with_vitality_tested():
    exam = ClinicalExaminationRecord(
        evidence_id="EVID-EX-001",
        tooth_fdi=36,
        pulp_vitality="non-vital",
        source_type=EvidenceSource.CLINICIAN_EXAMINATION,
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN,
    )
    wording = ClinicalAttributeEngine.format_caries_wording(
        pathology_class=PathologyClass.DEEP_CARIES,
        clinical_examinations=[exam],
        tooth_fdi=36,
    )
    assert "with pulp involvement confirmed by clinician vitality testing" in wording


# 3. Periodontal Bone Loss Blocker Tests
def test_bone_loss_without_probing_depth():
    wording = ClinicalAttributeEngine.format_bone_loss_wording(clinical_examinations=[], tooth_fdi=46)
    assert wording == "not supported in this version (no landmark data)"

def test_bone_loss_with_probing_depth_entered():
    exam = ClinicalExaminationRecord(
        evidence_id="EVID-EX-002",
        tooth_fdi=46,
        probing_depth_mm=6.0,
        source_type=EvidenceSource.CLINICIAN_EXAMINATION,
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN,
    )
    wording = ClinicalAttributeEngine.format_bone_loss_wording(
        clinical_examinations=[exam],
        tooth_fdi=46,
    )
    assert "periodontal pocketing recorded (6.0 mm)" in wording


# 4. Root Canal Failure Composite Rule Tests (3 Dedicated Tests)
def _create_mock_obs(tooth_fdi: int, pathology: PathologyClass):
    return RadiographicObservation(
        evidence_id=f"EVID-TEST-{tooth_fdi}-{pathology.value}",
        study_id="STUDY-TEST",
        radiograph_id="opg.png",
        finding_id=f"FIND-{tooth_fdi}-{pathology.value}",
        pathology_candidate=pathology,
        confidence=0.85,
        annotation_modality="detection_bounding_box",
        tooth_fdi=tooth_fdi,
        model_id="dentex-yolov8n-seg",
        model_version="1.0.0",
        source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )

def test_root_canal_failure_rct_only_no_flag():
    # Tooth has root canal treatment only -> NO flag
    obs_list = [_create_mock_obs(46, PathologyClass.ROOT_CANAL_TREATMENT)]
    flagged, msg = ClinicalAttributeEngine.evaluate_endodontic_failure(obs_list, tooth_fdi=46)
    assert flagged is False
    assert msg is None

def test_root_canal_failure_lesion_only_no_flag():
    # Tooth has periapical lesion only -> NO flag
    obs_list = [_create_mock_obs(46, PathologyClass.PERIAPICAL_LESION)]
    flagged, msg = ClinicalAttributeEngine.evaluate_endodontic_failure(obs_list, tooth_fdi=46)
    assert flagged is False
    assert msg is None

def test_root_canal_failure_both_coexist_flags_alert():
    # Tooth has BOTH root canal treatment and periapical lesion -> FLAGS alert with hedged wording
    obs_list = [
        _create_mock_obs(46, PathologyClass.ROOT_CANAL_TREATMENT),
        _create_mock_obs(46, PathologyClass.PERIAPICAL_LESION),
    ]
    flagged, msg = ClinicalAttributeEngine.evaluate_endodontic_failure(obs_list, tooth_fdi=46)
    assert flagged is True
    assert "Suspected persistent or recurrent periapical radiolucency" in msg
    assert "requires clinician review" in msg
