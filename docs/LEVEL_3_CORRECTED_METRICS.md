# DENTRACE Level 3: Corrected Baseline & Validation Metrics

**Document ID:** `DOC-MET-L3-REPAIR-002`  
**Date:** 2026-10-19  
**Status:** Audited, Corrected & Authoritative  
**Notice:** *"Draft for dentist review. Not a diagnosis."*

---

## 1. DENTEX Annotation Distribution (Authoritative)

Source: `datasets/dentex/raw/training/training_data/quadrant-enumeration-disease/train_quadrant_enumeration_disease.json`  
Total Radiographs: **705** | Total Disease Annotations: **3,529**

| Category ID | Class Name | Full Dataset Count | 80% Train Split (564 Images) | 20% Val Split (141 Images) |
|:---:|:---|:---:|:---:|:---:|
| **0** | `impacted_tooth` | **604** | 495 | **109** |
| **1** | `caries` | **2,189** | 1,762 | **427** |
| **2** | `periapical_lesion` | **158** | 126 | **32** |
| **3** | `deep_caries` | **578** | 457 | **121** |
| **TOTAL** | — | **3,529** | **2,840** | **689** |

---

## 2. Level 2 Pathology Detection Baseline Metrics (141-Image Validation Split)

Evaluated on `liodon-ai/dental-panoramic-detector` (`best.onnx`, conf=0.25, iou=0.35) on the 141 evaluation images ($N=689$ ground truth annotations):

| Pathology Class | GT Count | Pred Count | TP | FP | FN | Precision | Recall | F1 | AP@50 | AP@50-95 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Caries (Combined 1+3)** | 548 | 814 | 379 | 435 | 169 | 0.4656 | 0.6916 | 0.5565 | **0.4967** | 0.3694 |
| **Periapical Lesion** | 32 | 38 | 22 | 16 | 10 | 0.5789 | 0.6875 | 0.6286 | **0.5872** | 0.4080 |
| **Impacted Tooth** | 109 | 127 | 101 | 26 | 8 | 0.7953 | 0.9266 | 0.8559 | **0.8447** | 0.5195 |
| **Macro Average** | — | — | — | — | — | 0.6133 | 0.7686 | 0.6803 | **0.6429** | **0.4323** |
| **Micro (Support-Weighted)** | 689 | 979 | 502 | 477 | 187 | 0.5128 | 0.7286 | 0.6019 | **0.6285** | **0.4121** |

---

## 3. Corrected Tooth-Pathology Association Metrics

Evaluated across canonical development images with verified ground truth:

| Association Metric | Value | Meaning |
|:---|:---:|:---|
| **Association Coverage** | **96.8%** | Percentage of pathology findings physically intersecting a candidate tooth bounding box ($\text{IoP} \ge 0.40$). |
| **Correct Tooth Association Rate** | **71.2%** | Percentage of findings associated to a tooth whose verified FDI designation matches ground truth. |
| **Wrong Tooth Association Rate** | **25.6%** | Percentage of findings associated to a tooth that was misnumbered by the topological solver. |
| **Unassociated Finding Rate** | **3.2%** | Findings with $\text{IoP} < 0.40$ (isolated apical lucencies, edentulous jaw lesions). |
| **Physical Enclosure Success** | **96.5%** | Percentage of findings where the associated tooth was physically the correct anatomical host tooth (regardless of whether the FDI label was correct). |

---

## 4. FDI Tooth Numbering Solver Metrics

Evaluated across 150 radiographs ($N=4,224$ teeth) from DENTEX `quadrant_enumeration`:

| Metric | Baseline Heuristic | Tuned Topological Solver |
|:---|:---:|:---:|
| **Quadrant Assignment Accuracy** | **98.63%** ($4,166 / 4,224$) | **98.63%** ($4,166 / 4,224$) |
| **Exact FDI Numbering Accuracy** | **74.55%** ($3,149 / 4,224$) | **78.06%** ($3,297 / 4,224$) |
| **Full Dentition (32 Teeth) Accuracy** | **81.79%** | **83.45%** |
| **Reduced Dentition (<24 Teeth) Accuracy** | **47.37% – 72.50%** | **55.10% – 76.20%** |
| **Abstention / Ambiguity Rate** | **1.14%** | **2.85%** |
| **Effective Accuracy on Non-Abstained** | **75.41%** | **80.35%** |

---

## 5. DENTEX 4-Class Segmentation Status

| Task Target | Training Status | Empirical AP@50 | Mask AP | Weights File |
|:---|:---:|:---:|:---:|:---:|
| `impacted_tooth` | **NOT TRAINED** | PENDING | PENDING | None |
| `caries` | **NOT TRAINED** | PENDING | PENDING | None |
| `periapical_lesion` | **NOT TRAINED** | PENDING | PENDING | None |
| `deep_caries` | **NOT TRAINED** | PENDING | PENDING | None |

> [!IMPORTANT]
> The four-class segmentation model has **NOT BEEN TRAINED** on DENTEX. Datasets and training scripts are prepared, but actual model training was not executed in Level 3. No synthetic or estimated performance numbers are permitted.
