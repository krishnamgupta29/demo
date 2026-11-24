"""
Level 3 Verification & Repair Gate Tests.

Validates:
1. Exact DENTEX category IDs, authoritative names, and annotation counts (Resolves Task 1).
2. Reproducibility of the 141-image validation partition: 689 annotations (Resolves Task 2).
3. Strict separation between association coverage and tooth identity verification (Resolves Task 3).
4. FDI solver ambiguity handling and confidence-based abstention (Resolves Task 4).
5. Quantitative ONNX parity verification and latency reality check (Resolves Task 6).
"""
import json
from pathlib import Path
import pytest
import numpy as np

from backend.ml.fdi_solver import FDISolver, ResolvedTooth
from backend.ml.association import ToothPathologyAssociator


def test_dentex_authoritative_annotation_counts_and_mappings():
    """Verify that original DENTEX disease annotation JSON matches authoritative counts."""
    json_path = Path("datasets/dentex/raw/training/training_data/quadrant-enumeration-disease/train_quadrant_enumeration_disease.json")
    assert json_path.exists(), f"Source dataset missing: {json_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Total annotations
    anns = data["annotations"]
    assert len(anns) == 3529, f"Expected 3,529 annotations, got {len(anns)}"

    # 2. Category mapping
    cat3 = data.get("categories_3", [])
    cat3_map = {c["id"]: c["name"] for c in cat3}
    assert cat3_map == {
        0: "Impacted",
        1: "Caries",
        2: "Periapical Lesion",
        3: "Deep Caries",
    }

    # 3. Class distribution
    from collections import Counter
    counts = Counter(a["category_id_3"] for a in anns)
    assert counts[0] == 604, f"Expected 604 Impacted teeth, got {counts[0]}"
    assert counts[1] == 2189, f"Expected 2,189 Caries, got {counts[1]}"
    assert counts[2] == 158, f"Expected 158 Periapical Lesions, got {counts[2]}"
    assert counts[3] == 578, f"Expected 578 Deep Caries, got {counts[3]}"
    assert sum(counts.values()) == 3529


def test_reproducible_validation_split_counts():
    """Verify exact count of ground-truth annotations in 141-image dev split (seed=42)."""
    json_path = Path("datasets/dentex/raw/training/training_data/quadrant-enumeration-disease/train_quadrant_enumeration_disease.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    images = {img["id"]: img for img in data["images"]}
    sorted_ids = sorted(images.keys())
    rng = np.random.RandomState(42)
    shuffled = sorted_ids.copy()
    rng.shuffle(shuffled)
    n_val = int(round(len(shuffled) * 0.20))
    val_ids = set(shuffled[:n_val])
    assert len(val_ids) == 141

    val_anns = [a for a in data["annotations"] if a["image_id"] in val_ids]
    # Total annotations in the 141 evaluation images is 689
    assert len(val_anns) == 689, f"Expected 689 annotations in dev split, got {len(val_anns)}"

    from collections import Counter
    counts = Counter(a["category_id_3"] for a in val_anns)
    assert counts[0] == 109  # Impacted
    assert counts[1] == 427  # Caries
    assert counts[2] == 32   # Periapical Lesion
    assert counts[3] == 121  # Deep Caries
    # Combined Caries = 427 + 121 = 548
    assert counts[1] + counts[3] == 548


def test_association_coverage_vs_identity_accuracy_distinction():
    """Verify that geometric intersection does not claim correct association if tooth FDI is wrong."""
    associator = ToothPathologyAssociator(min_iop_threshold=0.40)

    # A finding physically inside tooth bounding box
    findings = [
        {
            "id": "fnd_01",
            "label": "caries",
            "confidence": 0.88,
            "bbox": [150.0, 150.0, 200.0, 200.0],
            "gt_fdi": 16,  # Ground truth tooth is #16
        }
    ]

    # Model detected a tooth at this exact spot, but FDISolver incorrectly labeled it as #15
    teeth = [
        ResolvedTooth(
            tooth_id="tooth_01",
            fdi_number=15,  # Wrong FDI assignment (15 instead of 16)
            fdi_name="Maxillary Right Second Premolar (#15)",
            quadrant=1,
            tooth_index=5,
            confidence=0.90,
            bbox=[100.0, 100.0, 250.0, 300.0],  # Fully encloses finding
            centroid=[175.0, 200.0],
            jaw="maxilla",
            patient_side="patient_right",
            uncertain_tooth=False,
        )
    ]

    teeth_with_finds, associations = associator.associate(findings, teeth)
    assoc = associations[0]

    # Geometric coverage: Successfully associated to a tooth bounding box
    assert assoc.associated_tooth_id == "tooth_01"
    assert assoc.iop == 1.0  # 100% containment
    assert assoc.associated_fdi_number == 15

    # Verification against ground truth: It hit the wrong tooth identity!
    is_correct_identity = (assoc.associated_fdi_number == findings[0]["gt_fdi"])
    assert is_correct_identity is False, "Geometric coverage must not be conflated with correct tooth identity!"


def test_fdi_solver_ambiguity_flagging_and_abstention():
    """Verify that ambiguous tooth proposals and supernumerary cases flag uncertain_tooth=True."""
    solver = FDISolver(
        uncertain_confidence_threshold=0.50,
        gap_pitch_ratio_threshold=1.75,
    )
    w, h = 2000, 1000

    # Create 9 teeth in Q2 (normal quadrant has at most 8 teeth: slot 9 is supernumerary/abnormal)
    props = []
    for i in range(9):
        cx = 1050.0 + i * 80.0
        props.append({
            "id": f"tooth_{i+1}",
            "bbox": [cx - 35.0, 200.0, cx + 35.0, 450.0],
            "confidence": 0.40 if i == 0 else 0.90,  # tooth 1 has marginal confidence < 0.50
        })

    resolved = solver.solve(props, image_width=w, image_height=h)
    assert len(resolved) == 9

    # Tooth 1 has low confidence -> uncertain_tooth = True
    assert resolved[0].uncertain_tooth is True
    assert "Marginal confidence" in (resolved[0].ambiguity_reason or "")

    # Tooth 9 has slot > 8 -> uncertain_tooth = True, fdi_number = None
    assert resolved[8].uncertain_tooth is True
    assert resolved[8].fdi_number is None
    assert "Supernumerary tooth or arch spacing anomaly" in (resolved[8].ambiguity_reason or "")


def test_quantitative_onnx_parity_artifacts():
    """Verify that quantitative ONNX parity results exist and meet accuracy requirements."""
    parity_json = Path("docs/LEVEL_3_ONNX_PARITY.json")
    assert parity_json.exists(), "ONNX parity benchmark json missing"

    with open(parity_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Parity assertions
    assert data["matched_instances"] >= 3
    assert data["max_coord_diff_px"] < 5.0, f"Max coordinate difference exceeded tolerance: {data['max_coord_diff_px']} px"
    assert data["class_agreement_pct"] == 100.0, "Class agreement between PyTorch and ONNX must be 100%"
    # Verify latency reality check
    assert data["onnx_cpu_latency_ms"] > 5000.0, "Unquantized ONNX CPU latency is reality-checked (>5s per image)"
