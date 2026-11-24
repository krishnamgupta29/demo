"""Unit tests for narrative quality, placeholder rejection, raw enum defense, and duplicate sentences."""

import pytest
from backend.schemas.finding import PathologyClass, FindingBoundingBox
from backend.schemas.evidence import (
    ClinicalEvidencePackage,
    RadiographicObservation,
    DentistFindingConfirmation,
    RequestedProcedureRecord,
    NarrativeStatementCitation,
    EvidenceSource,
    VerificationStatus,
)
from backend.schemas.clinician import ReviewDecision
from backend.clinical.faithfulness import FaithfulnessChecker


@pytest.fixture
def base_evidence_pkg():
    obs = RadiographicObservation(
        evidence_id="EVID-RAD-TEST-01",
        study_id="STUDY-TEST-01",
        radiograph_id="opg_01.png",
        finding_id="FIND-TEST-01",
        pathology_candidate=PathologyClass.DEEP_CARIES,
        confidence=0.85,
        annotation_modality="detection_bounding_box",
        tooth_fdi=46,
        model_id="dentex-yolov8n-seg",
        model_version="1.0.0",
        source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    proc = RequestedProcedureRecord(
        procedure_id="PROC-TEST-01",
        tooth_fdi=46,
        procedure_name="Molar Endodontic Therapy",
        suggested_cdt_code="D3330",
        clinician_rationale="Deep caries approaching pulp chamber.",
        source_type=EvidenceSource.CLINICAL_RATIONALE,
    )
    return ClinicalEvidencePackage(
        package_id="PKG-TEST-01",
        study_id="STUDY-TEST-01",
        radiograph_id="opg_01.png",
        ai_observations=[obs],
        requested_procedures=[proc],
    )


def test_reject_square_bracket_placeholders(base_evidence_pkg):
    """Rejects bracket placeholders like [coordinates and observations] while allowing authorized tags."""
    # Placeholder rejected
    bad_stmt = NarrativeStatementCitation(
        statement_id="STMT-PLACEHOLDER",
        section_index=5,
        section_title="Radiographic Observations",
        sentence_text="Panoramic radiograph reveals suspected deep caries on tooth #46 [coordinates and observations].",
        cited_evidence_ids=["EVID-RAD-TEST-01"],
        source_types=[EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    valid, issues = FaithfulnessChecker.evaluate_statement(bad_stmt, base_evidence_pkg)
    assert valid is False
    assert any("square-bracket placeholder" in iss.lower() for iss in issues)

    # Allowed tag [MISSING_EVIDENCE]
    allowed_stmt1 = NarrativeStatementCitation(
        statement_id="STMT-ALLOWED-1",
        section_index=5,
        section_title="Radiographic Observations",
        sentence_text="Panoramic radiograph reveals suspected deep caries on tooth #46 [MISSING_EVIDENCE].",
        cited_evidence_ids=["EVID-RAD-TEST-01"],
        source_types=[EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    valid1, issues1 = FaithfulnessChecker.evaluate_statement(allowed_stmt1, base_evidence_pkg)
    assert not any("square-bracket placeholder" in iss.lower() for iss in issues1)

    # Allowed tag [PENDING CLINICIAN REVIEW]
    allowed_stmt2 = NarrativeStatementCitation(
        statement_id="STMT-ALLOWED-2",
        section_index=5,
        section_title="Radiographic Observations",
        sentence_text="Panoramic radiograph reveals suspected deep caries on tooth #46 [PENDING CLINICIAN REVIEW].",
        cited_evidence_ids=["EVID-RAD-TEST-01"],
        source_types=[EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    valid2, issues2 = FaithfulnessChecker.evaluate_statement(allowed_stmt2, base_evidence_pkg)
    assert not any("square-bracket placeholder" in iss.lower() for iss in issues2)


def test_reject_raw_enum_names(base_evidence_pkg):
    """Rejects raw code identifiers with underscores (e.g. deep_caries, periapical_lesion, impacted_tooth)."""
    for raw_enum in ["deep_caries", "periapical_lesion", "impacted_tooth"]:
        bad_stmt = NarrativeStatementCitation(
            statement_id=f"STMT-RAW-{raw_enum}",
            section_index=5,
            section_title="Radiographic Observations",
            sentence_text=f"Panoramic radiograph reveals suspected {raw_enum} on tooth #46.",
            cited_evidence_ids=["EVID-RAD-TEST-01"],
            source_types=[EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION],
            verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
        )
        valid, issues = FaithfulnessChecker.evaluate_statement(bad_stmt, base_evidence_pkg)
        assert valid is False
        assert any("raw programming enum name" in iss.lower() for iss in issues)


def test_reject_duplicated_sentences_within_statement(base_evidence_pkg):
    """Rejects a statement where the model repeats the exact same sentence twice."""
    dup_stmt = NarrativeStatementCitation(
        statement_id="STMT-DUP-INTRA",
        section_index=5,
        section_title="Radiographic Observations",
        sentence_text="Suspected deep caries approaching the pulp was observed on tooth 46. Suspected deep caries approaching the pulp was observed on tooth 46.",
        cited_evidence_ids=["EVID-RAD-TEST-01"],
        source_types=[EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    valid, issues = FaithfulnessChecker.evaluate_statement(dup_stmt, base_evidence_pkg)
    assert valid is False
    assert any("duplicated sentence" in iss.lower() for iss in issues)


def test_reject_duplicated_sentences_across_sections(base_evidence_pkg):
    """Rejects narrative where Section 5 and Section 7 duplicate the exact same sentence."""
    stmt_sec5 = NarrativeStatementCitation(
        statement_id="STMT-S5",
        section_index=5,
        section_title="Radiographic Observations",
        sentence_text="Suspected deep caries approaching the pulp was observed on tooth 46.",
        cited_evidence_ids=["EVID-RAD-TEST-01"],
        source_types=[EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    stmt_sec7 = NarrativeStatementCitation(
        statement_id="STMT-S7",
        section_index=7,
        section_title="Clinical Rationale",
        sentence_text="Suspected deep caries approaching the pulp was observed on tooth 46.",
        cited_evidence_ids=["PROC-TEST-01"],
        source_types=[EvidenceSource.CLINICAL_RATIONALE],
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    result = FaithfulnessChecker.validate_narrative([stmt_sec5, stmt_sec7], base_evidence_pkg)
    assert result.is_faithful is False
    assert any("duplicated sentence across" in c.lower() for c in result.unsupported_claims)
