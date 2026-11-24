import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image
from backend.services.study_service import study_service
from backend.storage.file_manager import storage_manager
from backend.services.clinical_service import clinical_service

images = [
    ("sample_opg_1", "archive/sample_opg_images/sample_opg_1.png"),
    ("sample_opg_2", "archive/sample_opg_images/sample_opg_2.png"),
    ("sample_opg_3", "archive/sample_opg_images/sample_opg_3.png"),
    ("sample_opg_4", "archive/sample_opg_images/sample_opg_4.png"),
    ("dentex_train_0", "datasets/dentex/raw/training/training_data/quadrant-enumeration-disease/xrays/train_0.png"),
]

print("=== TASK 1 ACCEPTANCE: 5 REAL OPGS INFERENCE ===")
results = []
for label, rel_path in images:
    full_path = Path(rel_path)
    if not full_path.exists():
        print(f"File not found: {rel_path}")
        continue
    with open(full_path, "rb") as f:
        file_bytes = f.read()

    study = study_service.create_study(
        raw_bytes=file_bytes,
        original_filename=full_path.name,
        patient_anonymous_id=f"PT_{label}",
        modality="panoramic_opg",
    )
    study_id = study.study_id
    # Run default analysis (target_model=None -> defaults to dentex-yolov8n-seg with liodon merge)
    analysis = study_service.analyze_study(study_id=study_id, model_id=None)
    
    mask_count = sum(1 for f in analysis.findings if getattr(f, "has_mask", False))
    box_count = sum(1 for f in analysis.findings if not getattr(f, "has_mask", False))
    total = len(analysis.findings)
    results.append({
        "label": label,
        "study_id": study_id,
        "total": total,
        "mask_count": mask_count,
        "box_count": box_count,
    })
    print(f"[{label}] Total: {total} | Masks (has_mask=True): {mask_count} | Box-only: {box_count}")
    for idx, f in enumerate(analysis.findings):
        pts_len = len(f.polygon.points) if f.polygon and f.polygon.points else 0
        print(f"   Finding {idx+1}: {f.pathology_class.value} on FDI #{f.tooth_fdi} | has_mask={f.has_mask} | mask_vertices={pts_len} | conf={f.confidence:.2f}")

# Generate PDF for the first study to verify PDF overlay with masks
test_study_id = results[0]["study_id"]
pdf_bytes = clinical_service.export_claim_pack_pdf(test_study_id)
pdf_out_path = Path("scratch/task1_verified_claim_pack.pdf")
pdf_out_path.parent.mkdir(parents=True, exist_ok=True)
with open(pdf_out_path, "wb") as pf:
    pf.write(pdf_bytes)
print(f"\nPDF successfully generated with masks drawn: {pdf_out_path} ({len(pdf_bytes)} bytes)")
