import pytest
from backend.schemas.finding import PathologyFinding, PathologyClass, AnnotationModality, FindingBoundingBox
from backend.schemas.evidence import RadiographicObservation, DentistFindingConfirmation, ClinicalEvidencePackage, PayerPolicyTemplate, EvidenceSource, VerificationStatus
from backend.schemas.clinician import ReviewDecision
from backend.reporting.pdf_generator import LocalClaimPackPDFGenerator
from backend.clinical.narrative_generator import DeterministicNarrativeGenerator
from backend.clinical.evidence_engine import ClinicalEvidenceEngine

def test_fdi_uncertain_state_in_finding():
    finding = PathologyFinding(
        finding_id="FIND-TEST-001",
        study_id="STUDY-TEST",
        tooth_fdi=16,
        pathology_class=PathologyClass.CARIES,
        annotation_modality=AnnotationModality.DETECTION_BOUNDING_BOX,
        confidence=0.42,
        bbox=FindingBoundingBox(x_min=10.0, y_min=10.0, x_max=50.0, y_max=50.0),
        fdi_uncertain=True,
        fdi_status="ai_estimated",
    )
    assert finding.fdi_uncertain is True
    assert finding.fdi_status == "ai_estimated"

def test_fdi_confirmed_state_in_finding():
    finding = PathologyFinding(
        finding_id="FIND-TEST-002",
        study_id="STUDY-TEST",
        tooth_fdi=26,
        pathology_class=PathologyClass.CARIES,
        annotation_modality=AnnotationModality.DETECTION_BOUNDING_BOX,
        confidence=0.88,
        bbox=FindingBoundingBox(x_min=10.0, y_min=10.0, x_max=50.0, y_max=50.0),
        fdi_uncertain=False,
        fdi_status="clinician_confirmed",
    )
    assert finding.fdi_uncertain is False
    assert finding.fdi_status == "clinician_confirmed"

def test_pdf_rendering_both_fdi_states():
    # Package with one AI-estimated uncertain finding and one confirmed finding
    obs_uncertain = RadiographicObservation(
        evidence_id="EVID-UNC",
        study_id="STUDY-PDF-01",
        radiograph_id="rad_01.png",
        finding_id="FIND-UNC",
        pathology_candidate=PathologyClass.CARIES,
        confidence=0.45,
        annotation_modality=AnnotationModality.DETECTION_BOUNDING_BOX,
        bbox=FindingBoundingBox(x_min=100.0, y_min=100.0, x_max=200.0, y_max=200.0),
        tooth_fdi=16,
        fdi_uncertain=True,
        fdi_status="ai_estimated",
        model_id="dentex-yolov8n-seg",
        model_version="1.0.0",
        source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    
    obs_confirmed = RadiographicObservation(
        evidence_id="EVID-CFM",
        study_id="STUDY-PDF-01",
        radiograph_id="rad_01.png",
        finding_id="FIND-CFM",
        pathology_candidate=PathologyClass.DEEP_CARIES,
        confidence=0.91,
        annotation_modality=AnnotationModality.DETECTION_BOUNDING_BOX,
        bbox=FindingBoundingBox(x_min=300.0, y_min=100.0, x_max=400.0, y_max=200.0),
        tooth_fdi=46,
        fdi_uncertain=False,
        fdi_status="clinician_confirmed",
        model_id="dentex-yolov8n-seg",
        model_version="1.0.0",
        source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN,
    )

    cfm = DentistFindingConfirmation(
        evidence_id="EVID-CFM-DEC",
        finding_id="FIND-CFM",
        reviewer_name="Dr. Tester",
        license_number="LIC-12345",
        decision=ReviewDecision.CONFIRMED,
        confirmed_fdi=46,
        confirmed_pathology=PathologyClass.DEEP_CARIES,
        verification_status=VerificationStatus.CONFIRMED_BY_CLINICIAN,
    )

    package = ClinicalEvidencePackage(
        package_id="PKG-TEST-PDF",
        study_id="STUDY-PDF-01",
        radiograph_id="rad_01.png",
        ai_observations=[obs_uncertain, obs_confirmed],
        dentist_confirmations=[cfm],
        clinical_examinations=[],
        patient_symptoms=[],
        requested_procedures=[],
        payer_template=PayerPolicyTemplate(),
    )

    draft = DeterministicNarrativeGenerator.generate_draft(package)
    readiness = ClinicalEvidenceEngine.evaluate_package(package, radiograph_file_exists=False)
    pdf_bytes = LocalClaimPackPDFGenerator.generate_claim_pack_pdf(
        package=package,
        draft=draft,
        readiness=readiness,
    )
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")
