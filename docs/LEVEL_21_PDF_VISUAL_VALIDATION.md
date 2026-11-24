# LEVEL 21 — PDF VISUAL VALIDATION
**Detailed Structural & Visual Audit of the 5-Page Clinical Pre-Authorization PDF**

---

## 1. Document Overview

The DENTRACE Pre-Authorization Report Generator (`backend/reporting/pdf_generator.py`) produces an exact 5-page clinical document compiled via ReportLab. Every page is framed with running headers, footers, and the mandatory legal boundary disclaimer.

- **Document Format**: US Letter (612 × 792 pt, margins: 36 pt)
- **Palette**: Primary Indigo (`#282b4a`), Warm Neutral (`#eeebda`), Card Fill (`#f7f5ed`), Border (`#ded8c4`)
- **Total Pages**: Exactly 5 (verified via `pypdf.PdfReader` and `pypdfium2` rasterization)

---

## 2. Page-by-Page Audit

### Page 1 — Patient Summary & Case Intake
- **Masthead**: DENTRACE Clinical Decision Support System • Localhost Engine.
- **Mandatory Notice**: *"Draft for dentist review. Not a diagnosis. Requires licensed practitioner physical signature prior to treatment planning or payer submission."*
- **Patient Information Card**: Full Name, Case / MRN ID, Age & Sex, Scan Date, Attending Clinic, Findings Tally, Chief Complaint, and Relevant Dental History.
- **Technical Intake Quality Checklist**: Modality Verified (OPG), Exposure Quality Passed, 11-Tag PHI Sanitized, Zero Cloud Egress Verified (100% Localhost).
- **Evaluation Guidelines**: Maxillomandibular diagnostic protocol.

### Page 2 — Diagnostic Radiographic Evidence
- **Section Heading**: *"2. Diagnostic Radiographic Evidence (Full-Resolution Examination)"*
- **Radiograph Dual Comparison**:
  - Image A: Raw high-resolution panoramic radiograph (aspect ratio strictly preserved).
  - Image B: Calibrated neural anomaly reticles with ISO 3950 FDI localizations.
- **Acquisition Parameters Table**: Native dimensions (2872×1316 px), Aspect Ratio (2.18:1), 8-bit grayscale raster, Laplacian sharpness variance score, SHA-256 cryptographic digest.
- **Color Legend**:
  - AI Candidate: Bright Yellow (`#FACC15`)
  - Confirmed: Green (`#16A34A`)
  - Dismissed: Slate (`#64748B`)
  - Clinician Manual: Blue (`#0284C7`)

### Page 3 — Tooth-Wise Findings Ledger & Per-Tooth Crops
- **Section Heading**: *"3. Tooth-Wise Findings Ledger & Anatomical Assessment"*
- **Findings Table**: FDI Tooth #, Anatomical Nomenclature, Quadrant, Pathology Classification, AI Confidence Score, Review Status, Notes.
- **Per-Tooth Radiographic Detail Panels**: 3 crops per row, each showing a magnified radiograph region centered on the detected tooth with colored reticles.

### Page 4 — 3D Anatomical Spatial Model & Educational Reference
- **Section Heading**: *"4. 3D Anatomical Spatial Model & Educational Reference"*
- **Mandatory Anatomical Disclaimer**:
  *"Reference 3D Dental Anatomy — Not Patient-Specific. Rendered 3D visual geometry represents standard anatomical reference morphology. Tissue highlights are educational correlations and do NOT constitute volumetric patient reconstructions."*
- **3D Dental Arch Snapshot**: High-resolution snapshot with all affected teeth highlighted in bright yellow (`#FACC15`).
- **Histological & Biological Correlation Table**: Explains enamel, dentin, and pulp involvement for the active finding.
- **Arch Structural Disclosure**: Explains the 28 solid teeth + 4 translucent wisdom markers.

### Page 5 — Pre-Authorization Summary, CDT Coding & Attestation
- **Section Heading**: *"5. Pre-Authorization Summary, CDT Coding & Attestation"*
- **Proposed Procedures & CDT Coding Table**: Suggested CDT code (e.g. D2391, D3330), procedure name, tooth FDI, clinical necessity rationale.
- **Diagnostic Justification Narrative**: Synthesized clinical necessity statement.
- **Licensed Practitioner Attestation Block**: Checkbox attestation, Doctor Name, License #, Date, and pen-and-ink signature line.
- **Statutory Notice & SHA-256 Audit Seal**: Cryptographic proof of offline local generation.

---

## 3. Legal Boundary Verification

Every single page (Pages 1 through 5) contains:
- **Running Footer**: `Draft for dentist review. Not a diagnosis. Not certified under FDA / CE / MDR.`
- **Page Numbering**: `Page X of 5`
- **Draft Watermark**: Subtle non-intrusive 4% alpha watermark across draft exports.
