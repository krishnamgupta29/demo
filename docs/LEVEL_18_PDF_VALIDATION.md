# LEVEL 18 — 5-Page PDF Claim Pack Validation Report

**Document ID:** DENTRACE-L18-PDF  
**Author:** AI Systems Engineer  
**Date:** November 16, 2026  
**Status:** Validated & Formally Verified  

---

## 1. Document Architecture & Pagination

The DENTRACE Pre-Authorization Claim Pack is compiled via ReportLab into a formal 5-page PDF document:

| Page # | Title / Section | Contents & Clinical Evidence |
|---|---|---|
| **Page 1** | **Executive Diagnostic Summary** | Clinic branding, patient demographics (Name, Case ID, Age, Sex, Scan Date), Chief Complaint, Overall Diagnostic Summary, Modality Label (`Panoramic OPG` or `Intraoral Periapical`), Regulatory Disclaimers. |
| **Page 2** | **Primary Radiographic Evidence** | Full-width high-resolution radiograph with overlaid calibrated findings reticles, technical image metadata (resolution, aspect ratio, hash), and observation notes. |
| **Page 3** | **Selected Tooth Analysis & 3D Spatial Context** | High-magnification per-tooth cropped radiograph, isolated 3D dental arch screenshot showing highlighted FDI tooth, histological cutaway diagram, and tooth-level findings table. |
| **Page 4** | **Insurance Pre-Authorization & CDT Mapping** | Editable clinician clinical narrative, suggested procedure, primary CDT code (e.g. D2391, D7210), clinical necessity justification, and clinician attestation signature block. |
| **Page 5** | **Audit Trail, Provenance & Legal Governance** | Model version provenance, SHA-256 asset fingerprints, timestamped clinician action history, regulatory notices, and academic college research boundary statement. |

---

## 2. Multi-Modality PDF Support

When an **Intraoral Periapical (IOPA)** or **Bitewing** scan is processed:
1. Header displays `[IOPA] Intraoral Periapical Radiograph` or `[Bitewing] Bitewing Radiograph`.
2. Page 2 displays the IOPA scan at full diagnostic aspect ratio without distortion.
3. Automated AI findings section is replaced by:
   > *"Notice: Automated AI screener is validated strictly for Panoramic OPG. Modality flagged as Intraoral Periapical. All findings on this case represent direct clinician annotations."*
4. Page 4 CDT coding maps to periapical diagnostic imaging codes (e.g. D0220 - Intraoral periapical first radiographic image) alongside restorative procedures.

---

## 3. Visual & Layout Quality Standards
- **Typography:** Uses clean, readable Helvetica / Helvetica-Bold at $\ge 10\,\text{pt}$ body text for high readability.
- **Palette:** Clinical Dark Green (`#194241`), Slate Grey (`#687875`), High-Contrast Amber (`#D97706`), and White backgrounds.
- **Table Formatting:** Explicit cell wrapping, row striping, and zero clipping.
- **Disclaimers:** Fixed footer `"Draft for dentist review. Not a diagnosis."` on every single page.
