"""Unit tests for pathology-specific clinical wording and forbidden pairings (TASK F2)."""

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
from backend.clinical.narrative_generator import PATHOLOGY_RATIONALE_TEMPLATES


def _make_package(fdi: int, path_cls: PathologyClass):
    obs = RadiographicObservation(
        evidence_id="EVID-TEST-1",
        study_id="STUDY-PAIR-01",
        radiograph_id="opg.png",
        finding_id="F-1",
        pathology_candidate=path_cls,
        confidence=0.90,
        annotation_modality=AnnotationModality.DETECTION_BOUNDING_BOX,
        model_id="dentex-yolov8n-seg",
        model_version="1.0.0",
        bbox=FindingBoundingBox(x_min=100.0, y_min=200.0, x_max=300.0, y_max=400.0),
        tooth_fdi=fdi,
    )
    return ClinicalEvidencePackage(
        package_id="PKG-PAIR-01",
        study_id="STUDY-PAIR-01",
        radiograph_id="opg.png",
        ai_observations=[obs],
        payer_template=PayerPolicyTemplate(),
    )


def test_reject_periapical_lesion_with_restoration():
    """Periapical lesion paired with simple restoration must fail faithfulness."""
    pkg = _make_package(47, PathologyClass.PERIAPICAL_LESION)
    stmt = NarrativeStatementCitation(
        statement_id="STMT-FORBIDDEN-1",
        section_index=7,
        section_title="Clinical Rationale",
        sentence_text="Clinical evaluation is recommended for suspected periapical lesion on tooth #47 to provide composite restoration.",
        cited_evidence_ids=["EVID-TEST-1"],
        source_types=[EvidenceSource.CLINICAL_RATIONALE],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )
    is_valid, issues = FaithfulnessChecker.evaluate_statement(stmt, pkg)
    assert not is_valid, "Expected statement to fail due to periapical lesion + restoration pairing"
    assert any("Forbidden clinical pairing" in iss and "periapical lesion" in iss for iss in issues)


def test_reject_impacted_tooth_with_restore_function():
    """Impacted tooth paired with 'restore function' must fail faithfulness."""
    pkg = _make_package(48, PathologyClass.IMPACTED_TOOTH)
    stmt = NarrativeStatementCitation(
        statement_id="STMT-FORBIDDEN-2",
        section_index=7,
        section_title="Clinical Rationale",
        sentence_text="Clinical evaluation is recommended for suspected impacted tooth on tooth #48 to restore function.",
        cited_evidence_ids=["EVID-TEST-1"],
        source_types=[EvidenceSource.CLINICAL_RATIONALE],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )
    is_valid, issues = FaithfulnessChecker.evaluate_statement(stmt, pkg)
    assert not is_valid, "Expected statement to fail due to impacted tooth + restore function pairing"
    assert any("Forbidden clinical pairing" in iss and "impacted tooth" in iss for iss in issues)


def test_reject_unhedged_clinical_intervention_is_indicated():
    """Unhedged phrase 'Clinical intervention is indicated' must be rejected."""
    pkg = _make_package(16, PathologyClass.CARIES)
    stmt = NarrativeStatementCitation(
        statement_id="STMT-UNHEDGED",
        section_index=7,
        section_title="Clinical Rationale",
        sentence_text="Clinical intervention is indicated for tooth #16 to address suspected caries.",
        cited_evidence_ids=["EVID-TEST-1"],
        source_types=[EvidenceSource.CLINICAL_RATIONALE],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        uncertainty_preserved=True,
    )
    is_valid, issues = FaithfulnessChecker.evaluate_statement(stmt, pkg)
    assert not is_valid, "Expected statement to fail due to unhedged 'Clinical intervention is indicated'"
    assert any("Clinical intervention is indicated" in iss for iss in issues)


def test_hedged_pathology_templates_pass_faithfulness():
    """All approved pathology rationale templates must pass faithfulness validation."""
    test_cases = [
        (16, PathologyClass.CARIES),
        (26, PathologyClass.DEEP_CARIES),
        (47, PathologyClass.PERIAPICAL_LESION),
        (48, PathologyClass.IMPACTED_TOOTH),
        (36, PathologyClass.ROOT_CANAL_TREATMENT),
    ]

    for fdi, p_cls in test_cases:
        pkg = _make_package(fdi, p_cls)
        template_text = PATHOLOGY_RATIONALE_TEMPLATES[p_cls]
        stmt = NarrativeStatementCitation(
            statement_id=f"STMT-PASS-{p_cls.value}",
            section_index=7,
            section_title="Clinical Rationale",
            sentence_text=f"For tooth #{fdi}: {template_text}",
            cited_evidence_ids=["EVID-TEST-1"],
            source_types=[EvidenceSource.CLINICAL_RATIONALE],
            verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
            uncertainty_preserved=True,
        )
        is_valid, issues = FaithfulnessChecker.evaluate_statement(stmt, pkg)
        assert is_valid, f"Template for {p_cls.value} failed: {issues}"


def test_print_final_template_text(capsys):
    """Prints final template text as required by TASK F2."""
    print("\n--- FINAL PATHOLOGY-SPECIFIC RATIONALE TEMPLATES ---")
    for p_cls, template in PATHOLOGY_RATIONALE_TEMPLATES.items():
        print(f"[{p_cls.value}]: {template}")
    print("----------------------------------------------------\n")
    captured = capsys.readouterr()
    assert "caries" in captured.out
    assert "pending clinician confirmation" in captured.out
