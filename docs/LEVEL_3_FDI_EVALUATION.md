# DENTRACE Level 3: FDI Tooth Numbering & Association Evaluation

**Document Version:** 1.0.0  
**Date:** 2026-10-19  
**Status:** Complete & Verified  
**Regulatory Boundary:** *Draft for dentist review. Not a diagnosis. Academic decision-support prototype.*

---

## 1. Executive Summary

Panoramic dental radiographs (OPGs) present distinct topological challenges for automated tooth enumeration:
- Variations in patient head positioning and jaw tilt (Spee/Wilson curves)
- Missing teeth (agenesis, third molar impactions, extractions)
- Supernumerary or crowded dentition
- Overlapping dental restorations and metal artifacts

Prior to Level 3, the baseline system utilized raw detection proposals from `abychkov/dental-fdi-detection`, but left tooth numbering unassigned (`fdi_number=None`) due to class ambiguity in the raw proposals. 

In Level 3, an anatomical arch and topological solver (`FDISolver`) was engineered alongside a geometry-based association engine (`ToothPathologyAssociator`). Both components were evaluated against verified DENTEX ground truth annotations without synthetic fabrication.

---

## 2. Anatomical Solver Architecture (`FDISolver`)

The `FDISolver` implements the official ISO 3950 / FDI World Dental Federation two-digit notation:
- **Quadrant 1 (Maxillary Right / Radiological Left):** Teeth 18 down to 11
- **Quadrant 2 (Maxillary Left / Radiological Right):** Teeth 21 up to 28
- **Quadrant 3 (Mandibular Left / Radiological Right):** Teeth 31 up to 38
- **Quadrant 4 (Mandibular Right / Radiological Left):** Teeth 48 down to 41

### Algorithmic Pipeline:
```
[Raw Tooth Proposals]
       │
       ▼
1. Conservative Deduplication (Greedy NMS, IoU > 0.35)
       │
       ▼
2. Adaptive Occlusal Plane Split (Maxilla vs Mandible)
       │
       ▼
3. Dynamic Midline Estimation (Central Incisor Mass Center)
       │
       ▼
4. Monotonic Distance Sorting (Midline Outward)
       │
       ▼
5. Inter-Tooth Gap Pitch Analysis (Detecting Missing Teeth Slots)
       │
       ▼
6. Uncertainty & Anomaly Flagging (Slot > 8 or Conf < 0.50 -> uncertain_tooth = True)
       │
       ▼
[Resolved Teeth (11-48) with Uncertainty Metadata]
```

---

## 3. Quantitative Ground Truth Evaluation

The solver was evaluated across **150 panoramic radiographs** from DENTEX tooth enumeration annotations ($N=4,224$ ground truth teeth):

| Evaluation Metric | Measured Result | Benchmark Standard / Interpretation |
| :--- | :---: | :--- |
| **Radiographs Evaluated** | **150** | Development sample from DENTEX `quadrant_enumeration` |
| **Total Ground Truth Teeth** | **4,224** | Mean 28.16 teeth per patient |
| **Quadrant Assignment Accuracy** | **98.63%** ($4,166 / 4,224$) | High-reliability upper/lower & left/right spatial separation |
| **Exact FDI Numbering Accuracy** | **78.06%** ($3,297 / 4,224$) | Pure topological sequencing without manual clinician guidance |
| **Abstention / Uncertainty Flag Rate**| **2.85%** ($120 / 4,224$) | Transparently flagged as ambiguous, low-conf, or slot anomaly |
| **Accuracy on Non-Abstained Teeth** | **80.35%** | High reliability on confirmed tooth proposals |
| **Over-constraint (Forcing 32 teeth)**| **0.00%** | System dynamically respects actual detected dentition count |

### Clinical Insights on FDI Numbering Errors:
- The 98.63% quadrant accuracy confirms that adaptive occlusal splitting and bilateral midpoint estimation robustly partition the oral cavity into 4 quadrants.
- Exact FDI classification errors predominantly arise from **intra-quadrant serial shifts** (94.60% of all errors), specifically where missing premolars or anterior teeth cause distal teeth to shift by 1 slot.
- **Safety Directive:** In accordance with clinical safety principles, all predicted FDI tooth numbers are displayed with interactive clinician confirmation handles in the UI, enabling dentists to adjust or renumber missing slots with a single click.

---

## 4. Tooth-Pathology Association Engine Evaluation

The `ToothPathologyAssociator` links detected anomalies (Caries, Deep Caries, Periapical Lesion, Impacted Tooth) to host teeth using geometric containment:

### Metric Definitions:
- **Intersection over Pathology (IoP):**
  $$\text{IoP} = \frac{\text{Area}(\text{Finding} \cap \text{Tooth})}{\text{Area}(\text{Finding})}$$
  Measures the fraction of the lesion contained within the tooth contour. IoP is resilient to scale disparity (small caries pit inside a large molar).
- **Centroid Containment:** Verifies that the center point of the pathology lies inside the tooth bounding box or polygon mask.
- **Interproximal Resolution:** Identifies contact point lesions shared between two adjacent teeth ($\Delta \text{IoP} < 0.15$).

### Corrected Benchmark Results (Canonical Validation Partition):

| Association Scenario | Evaluated Findings ($N$) | Association Coverage | Correct Tooth Identity | Unassociated |
| :--- | :---: | :---: | :---: | :---: |
| **Canonical Single-Study Ingestion** | **689** | **96.8%** | **71.2%** | **3.2%** |
| **Cross-Subset Benchmark Evaluation** | 534 | 78.8% | 41.8% | 21.2% |

### Key Association Discoveries:
1. **Separation of Coverage vs Accuracy:** Finding geometric overlap ($\text{Coverage} = 96.8\%$) is decoupled from correct tooth identity assignment ($71.2\%$). The 25.6% difference is caused almost entirely by underlying FDI numbering errors (88.3% of association errors).
2. **Cross-Subset Image Dimension Mismatch:** Forensic inspection of DENTEX revealed that 622 out of 634 images in `quadrant_enumeration` and `quadrant-enumeration-disease` have differing resolutions (e.g. 1976x976 vs 2916x1316). Cross-subset bounding box evaluation without normalization produces artificial offsets. In production single-study inference, coordinate frames are identical.

---

## 5. Clinician-in-the-Loop Workflow Specification

To prevent erroneous clinical conclusions:
1. **Ambiguity Flagging:** Any tooth detection with confidence $< 0.50$ or slot $> 8$ is flagged `uncertain_tooth: True`.
2. **Interactive Overrides:** The API accepts a `clinician_fdi_override` payload:
   ```json
   {
     "tooth_id": "tooth_07",
     "corrected_fdi": 16,
     "clinician_notes": "First molar present; tooth 15 previously extracted"
   }
   ```
3. **No Autonomous Approval:** Insurance claim pre-authorization documents generated in downstream levels will reflect verified FDI designations only after clinician confirmation.
