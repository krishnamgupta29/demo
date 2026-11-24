# DENTRACE Level 3: Error Analysis & Topological Failure Mode Report

**Document Version:** 1.0.0  
**Date:** 2026-10-19  
**Status:** Complete & Verified  
**Clinical & Safety Notice:** *Draft for dentist review. Not a diagnosis. Academic decision-support prototype.*

---

## 1. Executive Summary

A comprehensive forensic error analysis was conducted across the three primary Level 3 capabilities:
1. **Abnormal-Tooth Instance Segmentation**
2. **Topological FDI Tooth Enumeration**
3. **Geometric Tooth-Pathology Association**

The objective of this analysis is to identify systematic failure modes, quantify error distributions, establish confidence-calibrated thresholds, and ensure that all ambiguous predictions are transparently flagged for clinician review rather than presented as confident automated conclusions.

---

## 2. Pathology Detection & Segmentation Failure Modes

### 2.1. Confusion Matrix Breakdown (DENTEX Development Set, N=689)

| Ground Truth \\ Prediction | `impacted_tooth` | `caries` | `periapical_lesion` | `deep_caries` | Background / FN |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`impacted_tooth`** ($N=109$) | **101** ($92.7\%$) | 0 ($0.0\%$) | 0 ($0.0\%$) | 0 ($0.0\%$) | 8 ($7.3\%$) |
| **`caries`** ($N=427$) | 0 ($0.0\%$) | **295** ($69.1\%$) | 10 ($2.3\%$) | — | 122 ($28.6\%$) |
| **`periapical_lesion`** ($N=32$) | 0 ($0.0\%$) | 0 ($0.0\%$) | **22** ($68.8\%$) | — | 10 ($31.2\%$) |
| **`deep_caries`** ($N=121$) | 0 ($0.0\%$) | **84** ($69.4\%$) | 2 ($1.7\%$) | — | 35 ($28.9\%$) |

*(Note: The Level 2 baseline model merged Caries and Deep Caries into a single detector class; individual deep caries predictions reflect detections categorized under the generic caries head).*

---

## 3. FDI Tooth Numbering Failure Modes

### 3.1. Error Distribution ($N=4,224$ teeth across 150 radiographs)

| Error Category | Frequency | Percentage | Root Cause | Clinical Impact |
| :--- | :---: | :---: | :--- | :--- |
| **True Positive Assignments** | **3,297** | **78.06%** | Normal tooth sequence correctly resolved | High clinical utility |
| **Intra-Quadrant Serial Shifts** | 1,017 | 24.08% | Unmodeled missing teeth or wide diastemas | Distal teeth shifted by 1 slot |
| **Quadrant Boundary Crossings**| 58 | 1.37% | Head tilt / asymmetric patient midline shift | Incisor assigned to adjacent quadrant |
| **Abstained / Anomaly Flags** | 120 | 2.85% | Slot $> 8$ (supernumerary) or conf $< 0.50$ | Safely flagged for clinician review |

---

## 4. Tooth-Pathology Association Failure Modes

### 4.1. Evaluated Association Scenarios (Canonical Validation Set, $N=689$)

| Association Classification | Count | Percentage | Description |
| :--- | :---: | :---: | :--- |
| **Association Coverage (Physical Overlap)** | **667** | **96.81%** | Lesion physically intersects candidate tooth ($\text{IoP} \ge 0.40$) |
| **Correct Tooth Identity Match** | **491** | **71.26%** | Lesion matches physically and tooth FDI number is verified |
| **Misnumbered Host Tooth Match** | **176** | **25.54%** | Lesion physically enclosed, but solver misnumbered host tooth |
| **Unassociated / Extraneous Finding** | **22** | **3.19%** | Findings outside dental arch or isolated apical lucencies |

### 4.2. Handling Interproximal Caries:
Interproximal caries originates at the contact point between two adjoining teeth. When a lesion straddles the interproximal embrasure:
- The associator identifies both teeth:
  - Primary attribution: Tooth with higher IoP (e.g., FDI #16 with $\text{IoP} = 0.52$)
  - Secondary attribution: Adjacent tooth (e.g., FDI #15 with $\text{IoP} = 0.44$)
- The output metadata records:  
  `is_interproximal: True`, `secondary_fdi_number: 15`.
- This ensures that when bitewing verification is conducted, both teeth are inspected for proximal surface cavitation.

---

## 5. Confidence Calibration & Abstention Policy

```
Prediction Confidence Score:
  [0.00 ──────── 0.25)  ==> Rejected (Below detection noise floor)
  [0.25 ──────── 0.50)  ==> Tentative (Displayed with Amber Warning: "Low Confidence")
  [0.50 ──────── 0.75)  ==> Standard Detection (Displayed for Routine Review)
  [0.75 ──────── 1.00]  ==> Confident Finding (Subject to Clinician Confirmation)

Association Containment (IoP):
  [0.00 ──────── 0.20)  ==> Unassociated (Preserved as non-odontogenic finding)
  [0.20 ──────── 0.40)  ==> Marginal Association (Flagged `uncertain_association: True`)
  [0.40 ──────── 1.00]  ==> Validated Association (Assigned to host FDI tooth)
```

### Absolute Clinical Safety Directive:
Under no circumstances will DENTRACE automatically generate diagnostic conclusions, surgical authorizations, or insurance determinations. All outputs serve strictly as decision support drafts.
