# DENTRACE Level 3: FDI Tooth Numbering Failure Analysis

**Document ID:** `DOC-ANA-L3-REPAIR-003`  
**Date:** 2026-10-19  
**Sample Evaluated:** 150 Panoramic Radiographs ($N=4,224$ teeth) from DENTEX `quadrant_enumeration`  
**Notice:** *"Draft for dentist review. Not a diagnosis."*

---

## 1. Executive Summary

A forensic breakdown of tooth identification and FDI numbering was conducted to identify the physical, anatomical, and mathematical causes of the ~22% error rate in deterministic FDI assignment.

```
Total Teeth Evaluated: 4,224
Overall Quadrant Accuracy: 98.63% (4,166 / 4,224)
Overall Exact FDI Accuracy: 74.55% - 78.06%
```

---

## 2. Failure Mode Categorization

All errors were decomposed into two mutually exclusive classes:

| Error Category | Occurrences | % of All Errors | Root Cause |
|:---|:---:|:---:|:---|
| **Intra-Quadrant Serial Shift** | **1,017** | **94.60%** | Off-by-one domino shift caused by unmodeled missing teeth or false gap detections. |
| **Quadrant Partition Error** | **58** | **5.40%** | Midline crossing or occlusal border assignment error. |

---

## 3. Directional Shift Breakdown (Pred Position − GT Position)

| Shift Amount | Occurrences | Clinical Scenario |
|:---:|:---:|:---|
| **Shift −1** | **539** (50.1%) | An anterior tooth or premolar was missing (extracted/congenitally absent). The solver failed to detect the gap, causing all distal teeth in the quadrant to be numbered 1 slot too medial (e.g. Tooth 16 labeled as 15). |
| **Shift +1** | **332** (30.9%) | A wide natural diastema or anatomical spacing between teeth was falsely interpreted as a missing tooth slot, causing distal teeth to be numbered 1 slot too distal (e.g. Tooth 15 labeled as 16). |
| **Shift −2** | **90** (8.4%) | Two anterior teeth missing (e.g. both central and lateral incisors missing). |
| **Shift −9 / −8** | **44** (4.1%) | Supernumerary proposal triggering slot overflow (>8) and fallback. |
| **Other Shifts** | **12** (1.1%) | Complex multi-tooth edentulism or severe crowding. |

---

## 4. Breakdown by Anatomical Region

### 4.1. By Jaw
- **Maxilla (Upper Jaw):** **78.32%** Accuracy ($1,651 / 2,108$). Wider anterior teeth and clearer occlusal separation.
- **Mandible (Lower Jaw):** **70.79%** Accuracy ($1,498 / 2,116$). Lower incisors are narrow ($<60$ px) and frequently crowded, increasing shift sensitivity.

### 4.2. By Quadrant
- **Q1 (Maxillary Right):** **78.81%** ($833 / 1,057$)
- **Q2 (Maxillary Left):** **77.83%** ($818 / 1,051$)
- **Q3 (Mandibular Left):** **71.67%** ($759 / 1,059$)
- **Q4 (Mandibular Right):** **69.91%** ($739 / 1,057$)

### 4.3. Monotonic Posterior Degradation
Because serial counting proceeds outward from the midline, errors accumulate distally:

| Tooth Position | Common Name | Accuracy (%) |
|:---:|:---|:---:|
| **Position 1** | Central Incisor | **82.05%** |
| **Position 2** | Lateral Incisor | **81.57%** |
| **Position 3** | Canine | **80.31%** |
| **Position 4** | First Premolar | **79.22%** |
| **Position 5** | Second Premolar | **73.24%** |
| **Position 6** | First Molar | **68.54%** |
| **Position 7** | Second Molar | **63.27%** |
| **Position 8** | Third Molar (Wisdom Tooth) | **61.03%** |

---

## 5. Impact of Missing Teeth (Edentulism)

| Dentition in Radiograph | Accuracy (%) | Error Characteristic |
|:---|:---:|:---|
| **Full Dentition (32 Teeth)** | **81.79%** | Mostly crowded lower incisor shifts. |
| **28 Teeth (Missing 4 Wisdom Teeth)** | **81.49%** | Robust: missing 18/28/38/48 does not shift anterior teeth. |
| **26–27 Teeth** | **65.95% – 73.42%** | Premolar extraction spaces cause single shifts. |
| **<23 Teeth (Severe Edentulism)** | **41.30% – 47.37%** | Large multi-tooth gaps exceed simple pitch heuristics. |

---

## 6. Safety & Clinical Mitigation

1. **Never Present Uncertain Tooth Numbers as Facts:**  
   When gap pitch uncertainty, slot overflow ($>8$), or low confidence ($<0.50$) occurs, the system flags `uncertain_tooth = True` and sets `fdi_number = None` with an explicit reason (e.g. `"Supernumerary tooth or arch spacing anomaly"`).
2. **Clinician Confirmation Mandate:**  
   The UI must display provisional FDI assignments in an editable odontogram where the dentist can re-index shifted teeth before generating insurance narratives.
