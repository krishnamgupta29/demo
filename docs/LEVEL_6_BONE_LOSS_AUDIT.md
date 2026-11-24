# DENTRACE Level 6 — Alveolar Bone Loss Capability Audit & Blocker Analysis

**Document ID:** DENTRACE-L6-BONE-001  
**Status:** BLOCKED (UNSUPPORTED_MISSING_LANDMARKS)  
**Date:** October 2026  
**Clinical Standards:** 2017 AAP/EFP World Workshop Periodontitis Staging  

---

## 1. Executive Clinical Summary

Radiographic evaluation of periodontal bone loss (PBL) is a cornerstone of periodontitis diagnosis and staging. However, quantitative bone loss estimation cannot be ethically or scientifically performed without specific anatomical reference landmarks.

Because the local dataset (DENTEX) does not contain CEJ, alveolar crest, or apex annotations, and no validated local model exists for crest line extraction, DENTRACE enforces a **strict architectural blocker**:

> [!CAUTION]
> **Zero Fabrication Policy:** DENTRACE strictly refuses to synthesize, extrapolate, or fabricate alveolar bone loss percentages. The model candidate `boneloss-pan769-baseline` is formally marked as `MODEL_UNAVAILABLE` with reason `UNSUPPORTED_MISSING_LANDMARKS`.

---

## 2. Anatomical & Methodological Requirements for Bone Loss (AAP/EFP 2017)

Under the authoritative 2017 AAP/EFP (American Academy of Periodontology / European Federation of Periodontology) consensus classification, periodontitis staging by radiographic bone loss requires:

$$\text{PBL (\%)} = \frac{\text{Distance}(\text{CEJ}, \text{Alveolar Crest})}{\text{Distance}(\text{CEJ}, \text{Root Apex})} \times 100$$

### Mandatory Anatomical Landmarks
1. **Cementoenamel Junction (CEJ):** The anatomical boundary between the crown enamel and root cementum, serving as the biological baseline for physiological bone height ($1.0$ to $2.0\text{ mm}$ apical to the CEJ).
2. **Alveolar Bone Crest (ABC):** The most coronal level of the interdental alveolar septum.
3. **Root Apex (RA):** The anatomical tip of the tooth root, required to establish the total physiological root length.

### AAP/EFP Radiographic Staging Criteria
- **Stage I (Mild):** Coronal third bone loss ($< 15\%$).
- **Stage II (Moderate):** Coronal third bone loss ($15\% \text{ to } 33\%$).
- **Stage III (Severe):** Extending to mid-third of root and beyond ($> 33\%$).
- **Stage IV (Very Severe):** Extending to apical third of root ($> 66\%$).

---

## 3. Audit of Local Datasets & Candidate Repositories

### DENTEX Challenge Dataset Audit
- The DENTEX challenge annotations provide instance segmentation polygons for 4 categories of abnormal teeth:
  1. `Impacted tooth` (604 annotations)
  2. `Caries` (2,189 annotations)
  3. `Periapical lesion` (158 annotations)
  4. `Deep caries` (578 annotations)
- **Landmark Finding:** DENTEX does **NOT** contain CEJ coordinates, crestal polylines, or root apices.
- **Whole-Tooth Polygon Limitation:** Polygons encompass entire coronal and radicular tooth boundaries, omitting alveolar septal heights.

### BoneLoss-PAN769 Repository Audit
- **Source:** Academic baseline (`BoneLoss-PAN769`).
- **Input Contract:** Dual-stage U-Net / ResNet architecture requiring pre-calibrated landmark points.
- **Physical Weight Audit:** Pretrained weights are not hosted within local storage or open repositories without authenticated institutional access.
- **Network Egress Constraint:** In compliance with the zero-cloud-egress rule (`AGENTS.md`), unverified external weights cannot be pulled without explicit user authorization and local validation.

---

## 4. Architectural Implementation & Truthful Rejection

In `backend/services/model_adapter.py` and `backend/services/study_service.py`, the candidate is explicitly registered with an unbypassable blocker:

```python
boneloss_candidate = ModelRegistryEntry(
    model_id="boneloss-pan769-baseline",
    model_name="BoneLoss-PAN769 Alveolar Crest Line Detector",
    version="1.0.0",
    task=ModelTask.BONE_LOSS_ANALYSIS,
    architecture="ResNet50 / U-Net Crestline Estimator",
    supported_classes=["alveolar_bone_loss", "cej_line", "crestal_bone_line"],
    input_shape=(1, 3, 512, 1024),
    weight_rel_path="models/checkpoints/boneloss_pan769.onnx",
    license_terms="Academic Research Only",
    source_repository="https://github.com/academic-dental/BoneLoss-PAN769",
    blocker_reason=(
        "UNSUPPORTED_MISSING_LANDMARKS: Quantitative alveolar bone loss assessment requires reference landmarks "
        "(cementoenamel junction, alveolar crest line, root apex). DENTEX challenge annotations provide whole-tooth "
        "abnormal condition polygons, not crestal reference lines. Quantitative bone loss assessment is explicitly "
        "unsupported until anatomically valid reference landmarks are available. Fabricating bone loss is prohibited."
    ),
)
```

When requested via `POST /api/v1/studies/{study_id}/analyze?model_id=boneloss-pan769-baseline`:
1. The engine returns HTTP 200 with `status: "model_unavailable"`.
2. `findings_count` is strictly `0`.
3. The response `notice` returns the full blocker reason.
4. No periodontal bone loss CDT codes (e.g. D4341, D4342) are generated.

---

## 5. Verification & Test Evidence

The blocker behavior is automated and asserted in:
- `tests/test_level_6_optimization.py::test_boneloss_unsupported_blocker_enforcement` (Passed)
- `tests/test_level_6_optimization.py::test_api_analyze_with_unsupported_boneloss_model` (Passed)
