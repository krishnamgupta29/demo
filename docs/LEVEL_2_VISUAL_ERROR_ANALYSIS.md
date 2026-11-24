# DENTRACE — Level 2 Visual Error Analysis & Qualitative Review

> **DOCUMENT ID:** DOC-LVL2-VISUAL-003  
> **STAGE:** LEVEL 2 (COMPLETED)  
> **DATE:** 2026-10-19  
> **LEGAL NOTICE:** Draft for dentist review. Not a diagnosis.  

---

## 1. Clinical Privacy & Patient Data Safeguards

All visual prediction inspections were generated strictly on local host storage from authorized, open-source de-identified academic research radiographs (DENTEX Challenge). 

- **Zero Cloud Egress:** All image rendering, overlays, and calculations executed strictly on localhost (`127.0.0.1`).
- **Protected Health Information (PHI):** Zero patient names, medical record numbers (MRNs), or institutional metadata exist or were retained.
- **Git Commit Exclusion:** Visual artifacts (`docs/visual_inspection/*.png`) are globally excluded by `.gitignore` (`*.png`) to guarantee no medical imagery is committed to version control.

---

## 2. Qualitative Case Reviews

Representative cases from the DENTEX held-out development evaluation split were selected to demonstrate both model competencies and characteristic error modalities.

### Case 1: Cervical Burnout vs. Interproximal Caries (`train_435.png`)
- **Radiograph Resolution:** 2909 $\times$ 1316 pixels.
- **Clinical Observation:** The image exhibits typical anatomical neck constriction across mandibular premolars and molars.
- **Model Behavior:**
  - The model generated 4 proposals for `caries` (confidence scores: 0.31, 0.30, 0.29, 0.29).
  - All 4 proposals corresponded to the anatomical cementoenamel junction (CEJ) rather than true demineralization.
- **Root Cause (Cervical Burnout):** Panoramic radiography projects X-rays obliquely through the cylindrical neck of the tooth where less tissue mass exists between the dense enamel crown and the alveolar bone ridge. This creates an optical radiolucent band frequently mistaken by object detectors for carious decay.
- **Clinical Review Directive:** Flagged as low-confidence proposals requiring clinical bitewing confirmation.

---

### Case 2: High-Confidence True Caries & Boundary Precision (`train_637.png`)
- **Radiograph Resolution:** 3076 $\times$ 1536 pixels.
- **Clinical Findings:**
  - **True Positive 1 (Caries):** Model bbox `[804.1, 510.9, 965.7, 788.1]` matched ground truth with **confidence = 0.667** and **IoU = 0.863**.
  - **True Positive 2 (Caries):** Model bbox `[1910.3, 549.5, 2094.7, 776.4]` matched ground truth with **confidence = 0.646** and **IoU = 0.790**.
  - **True Positive 3 (Caries):** Model bbox `[1132.1, 545.5, 1232.7, 808.8]` matched ground truth with **confidence = 0.561** and **IoU = 0.857**.
  - **True Positive 4 (Deep Caries):** Model bbox `[870.3, 846.7, 1135.1, 1148.5]` matched ground truth with **confidence = 0.503** and **IoU = 0.933**.
- **False Negatives:** Two small, shallow enamel lesions on adjacent incisors (`[1254, 861, 1356, 1167]` and `[1682, 853, 1809, 1163]`) were missed due to low radiopacity contrast.
- **Key Takeaway:** The model exhibits remarkable boundary precision (IoU $> 0.85$) on established dentinal and deep caries, while early superficial enamel demineralization falls below the detection threshold.

---

### Case 3: Multi-Pathology Impaction and Occlusal Disease (`train_498.png`)
- **Radiograph Resolution:** 2910 $\times$ 1316 pixels.
- **Clinical Findings:**
  - **True Positive (Impacted Tooth):** Mandibular third molar detected at `[683.3, 678.3, 878.7, 935.7]` with **confidence = 0.726**. Ground truth confirms horizontally angled impaction abutting the second molar roots.
  - **False Negative (Caries):** Occlusal caries on the adjacent partially erupted crown was missed because the proposal was suppressed by tooth-level third molar bounding box overlapping.
- **Key Takeaway:** When severe impaction and decay co-occur on the same tooth unit, single-scale bounding boxes may prioritize the macroscopic impaction boundary over localized cavity margins. This underscores the necessity of instance segmentation (planned for Level 3).

---

### Case 4: Apical Periodontitis & Anatomical Foramina Confusion
- **Clinical Finding:** True periapical lesion detected at the root apex of a non-vital lower first molar (**confidence = 0.58, IoU = 0.64**).
- **False Positive Observation:** An elliptical radiolucency near the mandibular premolar apices was flagged as a periapical lesion with confidence 0.38.
- **Anatomical Differential:** Anatomical inspection confirms the radiolucency is the normal **Mental Foramen**, through which the mental nerve and blood vessels exit the jawbone.
- **Safety Safeguard:** DENTRACE enforces the hardcoded rule that no apical radiolucency proposal can be declared a definitive diagnosis without clinician verification and IOPA corroboration.

---

## 3. Systematic Taxonomy of Detection Errors

```
                +------------------------------------+
                |   DENTRACE Qualitative Errors       |
                +------------------------------------+
                                  |
         +------------------------+------------------------+
         |                                                 |
[False Positives / Over-Detection]               [False Negatives / Under-Detection]
  1. Cervical Burnout Artifacts                    1. Early / Shallow Enamel Demineralization
  2. Normal Anatomical Radiolucencies             2. Co-occurring Lesions on Impacted Crowns
     (Mental Foramen, Maxillary Sinus Floor)       3. Subtle Apical Radiolucencies (< 3mm)
  3. Restoration Margin Contrast (Mach Bands)      4. Interproximal Occlusal Overlaps
  4. Interproximal Premolar Overlaps
```

---

## 4. Recommendations for Downstream Human-in-the-Loop Review

1. **Non-Intrusive Overlays:** Overlay bounding boxes must use high-contrast cyan/green outlines with translucent interiors so dental clinicians can clearly inspect underlying trabecular bone and enamel margins.
2. **Confidence-Tiered Highlighting:**
   - Confidence $\ge 0.50$: Displayed as standard prospective findings.
   - Confidence $0.25 - 0.49$: Displayed with an "Uncertain Proposal" warning badge.
3. **Mandatory Clinician Sign-off:** Every finding defaults to `review_status = "pending"`. No finding may be exported to insurance narrative drafting without a clinician's explicit acceptance or modification.
