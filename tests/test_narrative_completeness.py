"""Unit tests for narrative completeness enforcement in FaithfulnessChecker (TASK F1)."""

import pytest
from backend.schemas.finding import PathologyClass, FindingBoundingBox, AnnotationModality
from backend.schemas.evidence import (
    ClinicalEvidencePackage,
    RadiographicObservation,
    NarrativeStatementCitation,
    EvidenceSource,
    VerificationStatus,
    PayerPolicyTemplate,
)
from backend.clinical.faithfulness import FaithfulnessChecker


def _create_package_with_findings(findings_data):
    observations = []
    for idx, (fdi, path_cls) in enumerate(findings_data):
        obs = RadiographicObservation(
            evidence_id=f"EVID-OBS-{idx+1}",
            study_id="STUDY-COMP-01",
            radiograph_id="opg.png",
            finding_id=f"F-{idx+1}",
            pathology_candidate=path_cls,
            confidence=0.88,
            annotation_modality=AnnotationModality.DETECTION_BOUNDING_BOX,
            model_id="dentex-yolov8n-seg",
            model_version="1.0.0",
            bbox=FindingBoundingBox(x_min=100.0, y_min=200.0, x_max=300.0, y_max=400.0),
            tooth_fdi=fdi,
        )
        observations.append(obs)

    return ClinicalEvidencePackage(
        package_id="PKG-COMP-01",
        study_id="STUDY-COMP-01",
        radiograph_id="opg.png",
        ai_observations=observations,
        payer_template=PayerPolicyTemplate(),
    )


def test_completeness_passes_when_all_findings_covered():
    """All findings grouped by pathology in narrative prose must pass completeness."""
    pkg = _create_package_with_findings([
        (16, PathologyClass.CARIES),
        (26, PathologyClass.CARIES),
        (47, PathologyClass.PERIAPICAL_LESION),
    ])

    stmt5 = NarrativeStatementCitation(
        statement_id="STMT-5",
        section_index=5,
        section_title="Radiographic Observations",
        sentence_text="Panoramic radiograph reveals suspected caries on teeth #16 and #26, and suspected periapical lesion on tooth #47.",
        cited_evidence_ids=["EVID-OBS-1", "EVID-OBS-2", "EVID-OBS-3"],
        source_types=[EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )
    stmt7 = NarrativeStatementCitation(
        statement_id="STMT-7",
        section_index=7,
        section_title="Clinical Rationale",
        sentence_text="Clinical evaluation and treatment planning is recommended for teeth #16, #26, and #47, pending clinician confirmation of this AI-assisted finding.",
        cited_evidence_ids=["EVID-OBS-1", "EVID-OBS-2", "EVID-OBS-3"],
        source_types=[EvidenceSource.CLINICAL_RATIONALE],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )

    res = FaithfulnessChecker.validate_narrative([stmt5, stmt7], pkg)
    assert res.is_faithful, f"Expected faithful, got: {res.unsupported_claims}"
    assert len(res.unsupported_claims) == 0


def test_completeness_fails_on_silent_omission():
    """Omitting a tooth/pathology silently must be rejected by FaithfulnessChecker."""
    pkg = _create_package_with_findings([
        (16, PathologyClass.CARIES),
        (26, PathologyClass.CARIES),
        (47, PathologyClass.PERIAPICAL_LESION),
    ])

    # Narrative only mentions tooth #47, silently omitting #16 and #26
    stmt5 = NarrativeStatementCitation(
        statement_id="STMT-5",
        section_index=5,
        section_title="Radiographic Observations",
        sentence_text="Panoramic radiograph reveals suspected periapical lesion on tooth #47.",
        cited_evidence_ids=["EVID-OBS-3"],
        source_types=[EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )
    stmt7 = NarrativeStatementCitation(
        statement_id="STMT-7",
        section_index=7,
        section_title="Clinical Rationale",
        sentence_text="Endodontic evaluation is recommended for tooth #47, pending clinician confirmation of this AI-assisted finding.",
        cited_evidence_ids=["EVID-OBS-3"],
        source_types=[EvidenceSource.CLINICAL_RATIONALE],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )

    res = FaithfulnessChecker.validate_narrative([stmt5, stmt7], pkg)
    assert not res.is_faithful, "Expected unfaithful due to silent omission of teeth #16 and #26"
    completeness_errors = [c for c in res.unsupported_claims if "COMPLETENESS" in c]
    assert len(completeness_errors) >= 2
    assert any("Tooth #16" in e for e in completeness_errors)
    assert any("Tooth #26" in e for e in completeness_errors)


def test_completeness_passes_with_explicit_additional_findings_line():
    """Omitted findings explicitly listed under 'Additional findings not addressed in this narrative:' pass."""
    pkg = _create_package_with_findings([
        (16, PathologyClass.CARIES),
        (26, PathologyClass.CARIES),
        (47, PathologyClass.PERIAPICAL_LESION),
    ])

    stmt5 = NarrativeStatementCitation(
        statement_id="STMT-5",
        section_index=5,
        section_title="Radiographic Observations",
        sentence_text=(
            "Panoramic radiograph reveals suspected periapical lesion on tooth #47.\n"
            "Additional findings not addressed in this narrative: Tooth #16 (caries), Tooth #26 (caries)."
        ),
        cited_evidence_ids=["EVID-OBS-1", "EVID-OBS-2", "EVID-OBS-3"],
        source_types=[EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )
    stmt7 = NarrativeStatementCitation(
        statement_id="STMT-7",
        section_index=7,
        section_title="Clinical Rationale",
        sentence_text="Endodontic evaluation is recommended for tooth #47, pending clinician confirmation of this AI-assisted finding.",
        cited_evidence_ids=["EVID-OBS-3"],
        source_types=[EvidenceSource.CLINICAL_RATIONALE],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )

    res = FaithfulnessChecker.validate_narrative([stmt5, stmt7], pkg)
    assert res.is_faithful, f"Expected faithful with additional findings line, got: {res.unsupported_claims}"
