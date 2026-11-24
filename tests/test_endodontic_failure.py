"""Unit tests demonstrating composite root canal failure detection."""

import pytest
from backend.schemas.finding import PathologyClass
from backend.schemas.evidence import (
    ClinicalEvidencePackage,
    RadiographicObservation,
    RequestedProcedureRecord,
    EvidenceSource,
    VerificationStatus,
)
from backend.clinical.attribute_engine import ClinicalAttributeEngine
from backend.clinical.narrative_generator import DeterministicNarrativeGenerator


def test_composite_endodontic_failure_evaluation():
    """Evaluates composite detection: Root canal treatment + periapical lesion on same tooth."""
    obs_rct = RadiographicObservation(
        evidence_id="EVID-RCT-01",
        study_id="STUDY-ENDO-01",
        radiograph_id="endo.png",
        finding_id="FIND-RCT-01",
        pathology_candidate=PathologyClass.ROOT_CANAL_TREATMENT,
        confidence=0.88,
        annotation_modality="detection_bounding_box",
        tooth_fdi=46,
        model_id="nsitnov-8024-seg",
        model_version="1.0.0",
        source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    obs_lesion = RadiographicObservation(
        evidence_id="EVID-LESION-01",
        study_id="STUDY-ENDO-01",
        radiograph_id="endo.png",
        finding_id="FIND-LESION-01",
        pathology_candidate=PathologyClass.PERIAPICAL_LESION,
        confidence=0.82,
        annotation_modality="instance_segmentation",
        tooth_fdi=46,
        model_id="dentex-yolov8n-seg",
        model_version="1.0.0",
        source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )

    # 1. Composite rule flags failure when both exist on tooth 46
    is_failed, alert_msg = ClinicalAttributeEngine.evaluate_endodontic_failure([obs_rct, obs_lesion], 46)
    assert is_failed is True
    assert "persistent or recurrent periapical radiolucency" in alert_msg.lower()

    # 2. Does NOT flag when RCT is on a different tooth (e.g. tooth 47)
    obs_rct_diff_tooth = obs_rct.model_copy(update={"tooth_fdi": 47})
    is_failed_diff, _ = ClinicalAttributeEngine.evaluate_endodontic_failure([obs_rct_diff_tooth, obs_lesion], 46)
    assert is_failed_diff is False

    # 3. Test narrative integration
    pkg = ClinicalEvidencePackage(
        package_id="PKG-ENDO-01",
        study_id="STUDY-ENDO-01",
        radiograph_id="endo.png",
        ai_observations=[obs_rct, obs_lesion],
        requested_procedures=[],
    )
    draft = DeterministicNarrativeGenerator.generate_draft(pkg)
    assert "recurrent periapical radiolucency" in draft.section_5_radiographic_observations.lower()
