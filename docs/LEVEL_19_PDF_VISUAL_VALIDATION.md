# LEVEL 19 — CLINICAL REPORT PDF (10 SECTIONS / 5 PAGES) VISUAL VALIDATION

**Generator:** `backend/reporting/pdf_generator.py` (ReportLab Platypus Engine)  
**Layout:** 5 Structured Pages, 10 Required Clinical Sections  
**Legal Attestation:** *"Draft for dentist review. Not a diagnosis. Not certified under FDA / CE / MDR."*

---

## 1. 10-Section Specification Mapping

| Section # | Section Name | PDF Page | Description & Rendering Rules |
|:---:|:---|:---:|:---|
| **1** | **Patient Intake & Demographics** | Page 1 | Patient Name, Age, Sex, Scan Date, Chief Complaint, Case ID, Referring Clinician. |
| **2** | **Original Unaltered Radiograph** | Page 1 | High-fidelity grayscale radiograph. Preserves original pixel values with zero cloud egress. |
| **3** | **Neural Annotated Radiograph** | Page 1 | Coloured reticles with bounding boxes, FDI numbers, confidence %, and review status tags. |
| **4** | **Tooth-Wise Examination Table** | Page 2 | 5-column ledger: Tooth / FDI, Suspected Pathology, AI / Manual Status, Clinician Verification, Detailed Notes. |
| **5** | **Selected Tooth Crops** | Page 3 | High-magnification cropped views of flagged teeth with reticle overlays for micro-detail inspection. |
| **6** | **3D Dental Arch Spatial Snapshot** | Page 4 | Photographic snapshot of the full dental arch with highlighted FDI tooth positions. |
| **7** | **Educational Anatomy Cutaway Snapshot** | Page 4 | 3D micro-CT cross-section showing enamel, dentin, pulp chamber, and root canals. |
| **8** | **Anatomical Correlation Notes** | Page 4 | Educational correlation notes mapping clinical findings to histological tooth layers. |
| **9** | **Clinician Review & Verification** | Page 5 | Confirmed findings, dismissed candidates (excluded from insurance), and clinical rationale. |
| **10** | **Pre-Authorization Summary & Audit Trail**| Page 5 | CDT procedure coding recommendations, licensed dentist attestation block, and audit history. |

---

## 2. Distinction Between AI Findings and Clinician Manual Annotations

In both the annotated radiograph reticles and the clinical ledger:
- **AI Candidates:** Displayed with Amber/Yellow reticles (`#ea580c` / `#FACC15`) and statistical confidence scores (e.g., `85.4% liodon-panoramic-screener`).
- **Clinician Manual Annotations:** Displayed with Medical Blue reticles (`#0284c7`), tagged as `[✎] CLINICIAN ANNOTATION`, labeled as `Manual / Clinician Entry`, and explicitly designated as direct clinician observation.
- **Confirmed Findings:** Green reticles (`#16a34a`) marked `[✓] CONFIRMED`.
- **Dismissed Candidates:** Slate grey reticles (`#94a3b8`) marked `[✕] DISMISSED` and explicitly excluded from insurance billing recommendations.

---

## 3. PDF Header & Footer Layout

Every page is rendered using `DentraceNumberedCanvas` with:
- **Running Header (y = 762 pt):** `DENTRACE | Study ID: CASE-XXXX | Radiographic Decision Support | Zero Cloud Egress • Localhost 127.0.0.1`
- **Subtle Watermark:** `CLINICAL REVIEW DRAFT — NOT FOR SUBMISSION` at 45° angle with low opacity.
- **Regulatory Running Footer (y = 20 pt):** `Draft for dentist review. Not a diagnosis. Not certified under FDA / CE / MDR.`
- **Page Numbering:** `Page X of 5`.
