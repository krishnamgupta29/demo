# DENTRACE Level 6 — FDI Tooth Identification & Calibration Report

**Document ID:** DENTRACE-L6-FDI-001  
**Status:** AUDITED & EMPIRICALLY BENCHMARKED  
**Date:** October 2026  
**Standards:** ISO 3950 / FDI Two-Digit Tooth Notation  

---

## 1. Executive Summary & Problem Investigation

The baseline FDI topological arch solver achieved an apparent exact tooth identification accuracy of **78.06%** in initial Level 3 benchmarks. A comprehensive audit across 150 panoramic radiographs evaluating 4,224 ground-truth teeth revealed:

- **Total Teeth Evaluated:** 4,224
- **Baseline Correct Predictions:** 3,149 (74.55%)
- **Baseline Quadrant Accuracy:** 4,166 (98.63%)
- **Intra-Quadrant Shift Errors:** 94.6% of all misclassifications occurred within the correct quadrant.
  - Off-by-one under-enumeration (Shift -1): 539 instances
  - Off-by-one over-enumeration (Shift +1): 332 instances
  - Off-by-two or greater: 129 instances
  - Cross-quadrant or midline crossing errors: only 58 instances (1.37%)

### Root Cause Analysis
1. **Uniform Pitch Assumption:** The naive solver assumed teeth have equal inter-centroid spacing across the arch. In human dentition, molar widths (~1.30–1.40x) and premolar widths (~0.95–1.05x) differ substantially from central and lateral incisors (~0.75–0.90x).
2. **Missing Wisdom Teeth (FDI x8) & Extractions:** Adult patients frequently present with congenitally absent or surgically extracted third molars. A rigid sequence from midline outwards mislabels first molars as second molars when pitch gaps are not scaled dynamically.
3. **Midline Offset:** Asymmetric central incisor positioning shifted starting quadrant enumeration when using raw image center ($W / 2$) instead of the detected incisal embrasure.

---

## 2. Anatomical Prior Architecture & Pitch Scaling

DENTRACE implemented the `CalibratedFDISolver` extending the base arch solver with anatomical tooth width pitch scaling factors:

### Maxillary Tooth Width Scale Factors (`MAXILLA_WIDTH_FACTORS`)
- **Central Incisor (#11, #21):** $1.00$
- **Lateral Incisor (#12, #22):** $0.85$ (narrower crown)
- **Canine (#13, #23):** $0.95$
- **First Premolar (#14, #24):** $0.95$
- **Second Premolar (#15, #25):** $0.95$
- **First Molar (#16, #26):** $1.35$ (broad occlusal table)
- **Second Molar (#17, #27):** $1.30$
- **Third Molar (#18, #28):** $1.20$

### Mandibular Tooth Width Scale Factors (`MANDIBLE_WIDTH_FACTORS`)
- **Central Incisor (#41, #31):** $0.75$ (narrowest tooth in human dentition)
- **Lateral Incisor (#42, #32):** $0.80$
- **Canine (#43, #33):** $0.90$
- **First Premolar (#44, #34):** $0.95$
- **Second Premolar (#45, #35):** $0.95$
- **First Molar (#46, #36):** $1.40$ (largest lower tooth)
- **Second Molar (#47, #37):** $1.35$
- **Third Molar (#48, #38):** $1.25$

---

## 3. Parameter Sweep & Optimization Results

A deterministic grid search was executed over gap pitch ratio thresholds ($1.15$ to $1.65$) and midline gap thresholds ($0.90$ to $1.40$) on the validation dataset:

| Configuration | Gap Ratio | Midline Ratio | Exact Accuracy (%) | Non-Abstained Precision (%) | Abstained Count | Coverage (%) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| Baseline (Uncalibrated Level 3) | 1.75 | 2.20 | 74.55% | 75.37% | 46 (1.09%) | 98.91% |
| Config A (Conservative) | 1.25 | 1.05 | 75.82% | 76.88% | 58 (1.37%) | 98.63% |
| **Config B (Optimal Calibrated Level 6)** | **1.35** | **1.10** | **76.07%** | **76.55%** | **27 (0.64%)** | **99.36%** |
| Config C (High Abstention) | 1.15 | 0.95 | 74.91% | 77.20% | 125 (2.96%) | 97.04% |

### Key Improvements
- **Overall Exact Accuracy:** Improved from **74.55%** to **76.07%** (+1.52% absolute, +64 correct tooth designations across 4,224 teeth).
- **Precision on Non-Abstained Teeth:** Reached **76.55%** (vs 75.37% baseline).
- **Quadrant Integrity:** Maintained **98.63%** quadrant accuracy (4,166 / 4,224 teeth).
- **Abstention Policy:** 27 proposals with slot index $> 8$ (supernumerary or severe crowding) were safely abstained with `uncertain_tooth=True`, preventing cascading sequence errors down the quadrant while maintaining 99.36% coverage.


---

## 4. Coverage vs. Precision Trade-off Analysis

In medical decision-support systems, falsely asserting an erroneous tooth designation (e.g. labeling tooth #14 as #15) can lead to mismatched historical records or incorrect tooth-level treatment plans. 

1. **Selective Abstention:** Rather than forcing every detected proposal into an FDI number, proposals beyond the 8-tooth human quadrant limit or with ambiguous inter-tooth gaps are flagged as:
   ```json
   {
     "fdi_number": null,
     "uncertain_tooth": true,
     "ambiguity_reason": "Supernumerary tooth or arch spacing anomaly (slot > 8: tooth #9)"
   }
   ```
2. **Chairside Clinician Correction:** The Streamlit odontogram UI highlights uncertain teeth in amber, allowing the attending dentist to confirm or adjust the tooth designation with a single click.

---

## 5. Artifact Ledger

- Benchmark script: `scripts/benchmark_fdi_calibration.py`
- Empirical JSON report: `docs/level_6_fdi_benchmark.json`
- Calibrated solver code: `backend/ml/fdi_solver.py` (`CalibratedFDISolver`)
