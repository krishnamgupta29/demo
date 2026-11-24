import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.schemas.finding import PathologyClass, FindingBoundingBox, FindingPolygon
from backend.schemas.evidence import (
    ClinicalEvidencePackage,
    RadiographicObservation,
    ClinicalExaminationRecord,
    DentistFindingConfirmation,
    EvidenceSource,
    VerificationStatus,
)
from backend.clinical.evidence_engine import ClinicalEvidenceEngine
from backend.clinical.narrative_generator import DeterministicNarrativeGenerator
from backend.reporting.pdf_generator import LocalClaimPackPDFGenerator
from pypdf import PdfReader

def run_task5_pdf_acceptance():
    # Construct findings showcasing all Task 5 clinical attributes
    # 1. Impacted tooth #38 with polygon mask (PCA angulation)
    # 2. Deep caries on #46 without vitality recorded (hedged wording)
    # 3. Existing RCT + Periapical lesion on #16 (endodontic failure alert)
    # 4. Radiograph without bone probing depth (bone loss blocked)
    
    study_id = "STUDY-T5-ACCEPT"
    rad_id = "sample_opg_1.png"
    
    # Synthetic mesioangular mask points
    mesio_pts = [
        [100.0, 100.0], [130.0, 80.0], [160.0, 60.0], [190.0, 40.0],
        [180.0, 70.0], [150.0, 90.0], [120.0, 110.0]
    ]
    
    obs_imp = RadiographicObservation(
        evidence_id="EVID-OBS-38",
        study_id=study_id,
        radiograph_id=rad_id,
        finding_id="FIND-38",
        pathology_candidate=PathologyClass.IMPACTED_TOOTH,
        confidence=0.94,
        annotation_modality="instance_segmentation",
        bbox=FindingBoundingBox(x_min=1800.0, y_min=700.0, x_max=2000.0, y_max=950.0),
        polygon=FindingPolygon(points=mesio_pts),
        tooth_fdi=38,
        fdi_uncertain=False,
        model_id="dentex-yolov8n-seg",
        model_version="1.0.0",
        source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    
    obs_caries = RadiographicObservation(
        evidence_id="EVID-OBS-46",
        study_id=study_id,
        radiograph_id=rad_id,
        finding_id="FIND-46",
        pathology_candidate=PathologyClass.DEEP_CARIES,
        confidence=0.89,
        annotation_modality="instance_segmentation",
        bbox=FindingBoundingBox(x_min=700.0, y_min=750.0, x_max=850.0, y_max=950.0),
        tooth_fdi=46,
        fdi_uncertain=False,
        model_id="dentex-yolov8n-seg",
        model_version="1.0.0",
        source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    
    # Previous root canal treatment finding on 16
    obs_rct = RadiographicObservation(
        evidence_id="EVID-OBS-16-RCT",
        study_id=study_id,
        radiograph_id=rad_id,
        finding_id="FIND-16-RCT",
        pathology_candidate=PathologyClass.ROOT_CANAL_TREATMENT,
        confidence=0.91,
        annotation_modality="detection_bounding_box",
        bbox=FindingBoundingBox(x_min=600.0, y_min=300.0, x_max=750.0, y_max=500.0),
        tooth_fdi=16,
        fdi_uncertain=False,
        model_id="liodon-panoramic-screener",
        model_version="1.0.0",
        source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    
    # Periapical lesion finding on 16
    obs_lesion = RadiographicObservation(
        evidence_id="EVID-OBS-16-LES",
        study_id=study_id,
        radiograph_id=rad_id,
        finding_id="FIND-16-LES",
        pathology_candidate=PathologyClass.PERIAPICAL_LESION,
        confidence=0.87,
        annotation_modality="instance_segmentation",
        bbox=FindingBoundingBox(x_min=620.0, y_min=250.0, x_max=730.0, y_max=380.0),
        tooth_fdi=16,
        fdi_uncertain=False,
        model_id="dentex-yolov8n-seg",
        model_version="1.0.0",
        source_type=EvidenceSource.AI_RADIOGRAPHIC_OBSERVATION,
        verification_status=VerificationStatus.UNVERIFIED_AI_SUSPICION,
    )
    
    pkg = ClinicalEvidencePackage(
        package_id="PKG-T5-ACCEPT",
        study_id=study_id,
        radiograph_id=rad_id,
        radiograph_file_path="sample_opg_images/sample_opg_1.png",
        ai_observations=[obs_imp, obs_caries, obs_rct, obs_lesion],
        dentist_confirmations=[],
        clinical_examinations=[],
        requested_procedures=[],
    )
    
    # 1. Generate deterministic draft with Section 5 attributes
    draft = DeterministicNarrativeGenerator.generate_draft(pkg)
    readiness = ClinicalEvidenceEngine.evaluate_package(pkg, radiograph_file_exists=True)
    
    print("=" * 70)
    print("SECTION 5: RADIOGRAPHIC OBSERVATIONS NARRATIVE PARAGRAPH:")
    print("=" * 70)
    print(draft.section_5_radiographic_observations)
    print("=" * 70)
    
    # 2. Generate PDF
    out_pdf_path = Path("scratch/task5_verified_claim_pack.pdf")
    pdf_bytes = LocalClaimPackPDFGenerator.generate_claim_pack_pdf(
        pkg, draft, readiness, output_path=str(out_pdf_path)
    )
    out_pdf_path.write_bytes(pdf_bytes)
    print(f"\nGenerated PDF: {out_pdf_path} ({len(pdf_bytes)} bytes)")
    
    # 3. Read back text from PDF
    reader = PdfReader(str(out_pdf_path))
    print(f"Total Pages in PDF: {len(reader.pages)}")
    
    page4_text = reader.pages[3].extract_text() or ""
    print("\n--- PAGE 4 NARRATIVE TEXT IN GENERATED PDF ---")
    for line in page4_text.splitlines():
        if any(term in line.lower() for term in ["radiographic observations", "angulation", "deep caries", "approaching the pulp", "endodontic", "suspected"]):
            print(f"  [PDF PAGE 4]: {line.strip()}")

if __name__ == "__main__":
    run_task5_pdf_acceptance()
