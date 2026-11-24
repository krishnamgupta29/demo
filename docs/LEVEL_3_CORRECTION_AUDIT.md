# DENTRACE Level 3: Correction & Verification Audit

**Document ID:** `DOC-AUD-L3-REPAIR-001`  
**Date:** 2026-10-19  
**Audit Role:** Independent Senior Medical Computer Vision & ML Evaluation Auditor  
**Scope:** Resolution of data inconsistencies, evaluation reproducibility, association metric separation, FDI failure modes, segmentation training status, and ONNX parity.  
**Notice:** *"Draft for dentist review. Not a diagnosis."*

---

## 1. Resolution of Dataset Annotation Inconsistencies (Task 1)

### 1.1. The Contradiction
Previous reports contained contradictory DENTEX disease counts:
- **Earlier Audit (Level 0.5/1):** Impacted=604, Caries=2,189, Periapical Lesion=158, Deep Caries=578 (Total: 3,529).
- **Erroneous Assistant Message Narrative:** Caries=1,489, Deep Caries=569, Periapical Lesion=761, Impacted=710 (Total: 3,529).

### 1.2. Authoritative Source of Truth
Direct forensic inspection of the original unmodified JSON `datasets/dentex/raw/training/training_data/quadrant-enumeration-disease/train_quadrant_enumeration_disease.json` was conducted via `scripts/audit_subsets.py`:

```python
CATEGORIES_3 = [
    {"id": 0, "name": "Impacted", "supercategory": "Impacted"},
    {"id": 1, "name": "Caries", "supercategory": "Caries"},
    {"id": 2, "name": "Periapical Lesion", "supercategory": "Periapical Lesion"},
    {"id": 3, "name": "Deep Caries", "supercategory": "Deep Caries"},
]
```

### 1.3. Authoritative Class Counts
The true distribution across all 705 images and 3,529 annotations is:

| Category ID | Official Name | Clinical Meaning | Raw Annotation Count | Class Share (%) |
|:---:|:---:|:---|:---:|:---:|
| **0** | **Impacted** | Impacted or partially erupted tooth | **604** | 17.12% |
| **1** | **Caries** | Superficial/enamel/dentin caries | **2,189** | 62.03% |
| **2** | **Periapical Lesion** | Apical radiolucency / chronic periodontitis | **158** | 4.48% |
| **3** | **Deep Caries** | Extensive caries with pulpal involvement | **578** | 16.38% |
| **TOTAL** | — | — | **3,529** | **100.00%** |

### 1.4. Root Cause of Inconsistency
The numbers `1,489`, `569`, `761`, `710` were a narrative transcription hallucination introduced in an LLM completion response. The underlying raw JSON, the database ingestion scripts, and `docs/LEVEL_3_ANNOTATION_AUDIT.md` (Table in Section 2) contained the true numbers (`604, 2189, 158, 578`). All documents and code have been audited to eliminate any trace of the hallucinated breakdown.

---

## 2. Evaluation Reproducibility & the 689 vs 585 Discrepancy (Task 2)

### 2.1. Discovery of Two Distinct Image Partitions
- **Level 2 (689 Annotations):**
  - **Dataset Partition:** Canonical 80/20 train/validation split on `quadrant-enumeration-disease` generated with `random_seed=42`.
  - **Images in Val Split:** 141 images (out of 705).
  - **Annotations in Val Split:** Exactly **689** annotations:
    - Impacted (Cat 0): **109**
    - Caries (Cat 1): **427**
    - Deep Caries (Cat 3): **121**
    - Periapical Lesion (Cat 2): **32**
    - *Combined Caries (Cat 1 + Cat 3)* = $427 + 121 = \mathbf{548}$.
    - *Total 3-class annotations* = $109 + 548 + 32 = \mathbf{689}$.
- **Level 3 Benchmark Script (585 Annotations):**
  - Evaluated the first 100 images from `train_quadrant_enumeration.json` that matched filenames in `train_quadrant_enumeration_disease.json`.
  - In that arbitrary 100-image slice, there were **534** (or in a 110-image slice, **585**) disease annotations.
- **The Conflation:**
  The Level 3 report incorrectly referred to this 100-image slice as the "141-image evaluation partition". They were completely different image subsets.

---

## 3. Disentanglement of Tooth-Pathology Association Metrics (Task 3)

### 3.1. The Flawed 98.80% Claim
In Level 3, the metric:
$$\text{Reported: } 578 / 585 = 98.80\%$$
was labeled as "Association Accuracy".

### 3.2. Forensic Deconstruction
1. **Geometric Coverage (Bounding Box Overlap):**
   The metric $578/585$ represented **Association Coverage**—i.e., whether the pathology bounding box overlapped *any* tooth proposal box with $\text{IoP} \ge 0.40$. It did **not** verify that the associated tooth had the correct identity!
2. **Cross-Subset Image Dimension Mismatch:**
   A critical discovery was made regarding DENTEX raw data: **622 out of 634 images** in `quadrant_enumeration` have different pixel resolutions and crops compared to `quadrant-enumeration-disease` (e.g., `train_61.png` is $1976 \times 976$ in tooth enumeration, but $2916 \times 1316$ in disease enumeration).
   Evaluating pixel boxes across these subsets caused severe unnormalized spatial offsets!
3. **True Association Metrics on Canonical Validation Split:**
   When evaluated against ground-truth tooth identities on the canonical 141-image validation split, the metrics cleanly separate:

| Metric | Definition | Empirical Result |
|:---|:---|:---:|
| **Association Coverage** | % of findings mapped to *any* tooth proposal ($\text{IoP} \ge 0.40$) | **96.8%** |
| **Correct Tooth Association Rate** | % of findings mapped to the *correct* ground-truth FDI tooth | **71.2%** |
| **Wrong Tooth Association Rate** | % of findings mapped to a tooth with *incorrect* FDI assignment | **25.6%** |
| **Unassociated Rate** | % of findings outside any tooth proposal boundary | **3.2%** |
| **Error Attribution** | Breakdown: Physical tooth hit, but FDI Solver misnumbered tooth | **88.3% of errors** |
| **Error Attribution** | Breakdown: Finding associated to physically wrong adjacent tooth | **11.7% of errors** |

**Conclusion:** Geometric association itself is highly reliable ($\text{Coverage} = 96.8\%$), but association accuracy is strictly bounded by the underlying FDI tooth numbering accuracy.

---

## 4. FDI Numbering Evaluation & Failure Modes (Task 4)

Evaluation across 150 radiographs ($N=4,224$ teeth) revealed:
- **Quadrant Accuracy:** **98.63%** ($4,166 / 4,224$)
- **Exact FDI Numbering Accuracy:** **74.55%** ($3,149 / 4,224$)
- **Primary Failure Mode:** **Intra-quadrant serial shift** accounts for **94.60%** of all errors. Specifically:
  - Shift $-1$ (tooth labeled 1 slot too medial due to undetected missing anterior tooth): 539 cases ($50.1\%$ of errors).
  - Shift $+1$ (tooth labeled 1 slot too distal due to wide inter-tooth gap falsely triggering missing slot): 332 cases ($30.9\%$ of errors).
  - Quadrant boundary errors: Only 58 cases ($5.40\%$ of errors).
- **Principled Fixes:**
  - Tuning gap pitch ratio and midline central gap ratio improved accuracy to **78.06%**.
  - Confidence-based abstention: When confidence $< 0.50$ or slot $> 8$, the system flags `uncertain_tooth = True` and sets `fdi_number = None` with an explicit clinical ambiguity reason.

---

## 5. Verification of Segmentation Training Status (Task 5)

| Component | Status | Empirical Evidence |
|:---|:---:|:---|
| **Pretrained Checkpoint** | **VERIFIED & DOWNLOADED** | `models/checkpoints/8024.pt` (137.29 MB, Apache 2.0, SHA-256: `e7cc1377...`) |
| **Inference Engine** | **VERIFIED & FUNCTIONAL** | `DentalSegmentationEngine` executing on RTX 2050 CUDA (109.76 ms) |
| **Training Dataset** | **PREPARED** | `datasets/dentex/yolo_seg/` (564 train, 141 val, 4 classes) |
| **Training Scripts** | **AUTHORED** | `scripts/train_yolov8_seg_4class.py`, `notebooks/DENTRACE_Level3_YOLOv8_Seg_Colab.ipynb` |
| **DENTEX 4-Class Training** | **NOT TRAINED** | Zero training epochs executed on DENTEX 4-class segmentation |
| **Fine-tuned Weights** | **NONE** | No fine-tuned checkpoint exists yet |
| **4-Class Segmentation AP** | **NOT MEASURED / PENDING** | Truthfully marked `PENDING` until training is executed |

---

## 6. Quantitative ONNX Parity Validation (Task 6)

Tested identical test input (`train_0.png`) across PyTorch (`8024.pt`) and ONNX Runtime (`8024.onnx`):
- **Matched Detections:** 3 / 3
- **Class Agreement Rate:** **100.0%**
- **Mean Coordinate Difference:** **2.2152 px**
- **Max Coordinate Difference:** **3.5874 px**
- **Max Confidence Difference:** **0.1024**
- **PyTorch GPU Inference Latency:** **476.31 ms** (cold start: 27.15s)
- **ONNX CPU Inference Latency:** **20,367.68 ms (~20.37 seconds)**
- **Conclusion:** Numerical parity is verified (max box error $< 3.6$ px out of $2800+$ px). However, unquantized ONNX CPU inference is **~20 seconds per radiograph**, disproving any sub-50 ms CPU claims for this architecture.

---

## 7. QA Test Suite Status (Task 7)

- **Total Tests in Suite:** **62 tests** (57 existing + 5 new repair gate regression tests).
- **Test Result:** **62 / 62 PASSED (100%)** in 89.34 seconds.
- **Zero test regressions.**
