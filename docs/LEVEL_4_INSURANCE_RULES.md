# DENTRACE Level 4: Missing Evidence Detective & ADA CDT Coding Rules

**Document ID:** `DOC-INS-L4-002`  
**Date:** 2026-10-20  
**Status:** COMPLETE & AUTHORITATIVE  
**Notice:** *"Draft for dentist review. Not a diagnosis. Illustrative academic coding catalog."*

---

## 1. Missing Evidence Detective Architecture

The Missing Evidence Detective (`backend/clinical/detective.py`) is a deterministic inspection system that audits clinical packages prior to pre-authorization drafting.

### 1.1. Core Operating Principles
- **No Hallucinated Answers:** The detective never assumes facts. When pulp vitality, cavitation, or symptom duration is absent, it generates a structured inquiry rather than defaulting to "normal" or "necrotic".
- **Procedure-Specific Targeting:** Questions are generated solely for procedures that require them. If a simple resin composite is requested, the system does NOT ask for endodontic vitality tests or surgical flap justifications.
- **Mandatory Modality Rule:** Panoramic radiographs (OPG) have inherent magnification and focal trough distortion. When endodontic therapy is requested, the detective enforces the clinical requirement for an **Intraoral Periapical (IOPA)** radiograph to verify the root apex.

### 1.2. Specialty Checklist Matrix

| Clinical Procedure Group | Target Procedure Examples | Compulsory Evidentiary Checklist | Severity |
|---|---|---|:---:|
| **Endodontics** | Molar Root Canal (`D3330`), Premolar Root Canal (`D3320`) | 1. Pulp vitality test (`pulp_vitality` != untested)<br/>2. Percussion sensitivity test (`percussion_sensitivity`)<br/>3. Attached intraoral periapical radiograph (`IOPA`)<br/>4. Confirmed FDI host tooth number | **REQUIRED** |
| **Restorative Dentistry** | Posterior Resin Composite (`D2391`, `D2392`), Amalgam (`D2140`) | 1. Verified structural cavitation (`visual_cavitation = True`)<br/>2. Radiographic caries extending into dentin<br/>3. Verified FDI tooth number and surface specification | **REQUIRED** |
| **Oral Surgery** | Extraction (`D7140`, `D7210`), Bony Impaction Removal (`D7230`, `D7240`) | 1. Non-restorability indication (mobility grade, crown fracture)<br/>2. Angulation / impaction classification on radiograph<br/>3. Clinical rationale justifying extraction | **RECOMMENDED** |
| **Periodontics** | Scaling & Root Planing (`D4341`) | 1. Periodontal pocket probing depths $\ge 4.0\text{ mm}$ (`probing_depth_mm`)<br/>2. Radiographic crestal alveolar bone resorption<br/>3. Quadrant identifier | **REQUIRED** |

---

## 2. ADA CDT Demonstrative Coding Layer

Current Dental Terminology (CDT) is copyrighted by the American Dental Association (ADA). DENTRACE implements a demonstrative academic subset with explicit versioning and licensing notices:

- **Catalog Version:** `2026-Academic-Demo`
- **Catalog Source:** `ADA CDT Demonstrative Academic Subset (College Project)`
- **Effective Date:** `2026-01-01`
- **Legal Notice:** *"Code inclusion does not guarantee payer coverage, pre-authorization, or reimbursement. Verify against official current ADA CDT references."*

### 2.1. Demonstrative Code Specification Table

| CDT Code | Nomenclature Title | Specialty Category | Required Supporting Documentation |
|:---:|---|:---:|---|
| **D0140** | Limited Oral Evaluation - Problem Focused | Diagnostic | Chief complaint, focused clinical examination findings |
| **D0220** | Intraoral - Periapical First Radiographic Image | Diagnostic | Radiograph attachment, diagnostic indication |
| **D2140** | Amalgam - One Surface, Primary or Permanent | Restorative | Radiographic caries, verified FDI tooth, surface |
| **D2391** | Resin-Based Composite - One Surface, Posterior | Restorative | Radiographic caries into dentin, visual cavitation, tooth FDI |
| **D2392** | Resin-Based Composite - Two Surfaces, Posterior | Restorative | Radiographic caries, tooth FDI, involved surfaces (e.g. MO, DO) |
| **D3320** | Endodontic Therapy - Premolar Tooth | Endodontics | Periapical radiograph, pulp vitality test, percussion test, tooth FDI (positions 4–5) |
| **D3330** | Endodontic Therapy - Molar Tooth | Endodontics | Periapical radiograph, pulp vitality test, percussion test, tooth FDI (positions 6–8) |
| **D7140** | Extraction, Erupted Tooth or Exposed Root | Oral Surgery | Radiograph, non-restorable tooth rationale, tooth FDI |
| **D7210** | Surgical Extraction Requiring Bone Removal / Sectioning | Oral Surgery | Radiograph, surgical flap/sectioning rationale, tooth FDI |
| **D7230** | Removal of Impacted Tooth - Partially Bony | Oral Surgery | Radiograph, impaction classification, pericoronitis/pathology rationale |
| **D7240** | Removal of Impacted Tooth - Completely Bony | Oral Surgery | Radiograph, completely bony impaction classification |
| **D4341** | Periodontal Scaling & Root Planing - 4+ Teeth / Quadrant | Periodontics | Probing depth chart ($\ge 4\text{ mm}$), radiographic bone loss, quadrant |

### 2.2. Deterministic CDT Consistency Checker
The method `CDTCodingService.validate_code_consistency()` prevents illegal code combinations:
- Rejects `D3330` on premolars (e.g., Tooth #14, #15, #24, #25, #34, #35, #44, #45).
- Rejects `D3320` on molars (e.g., Tooth #16, #17, #18, #26, #27, #28, etc.).
- Rejects `D7230`/`D7240` (impacted surgical removal) if the proposed clinical procedure specifies simple erupted extraction without impaction.

---

## 3. Claim-to-Evidence Traceability Schema

Every sentence in the generated pre-authorization narrative carries structured citations linking it back to underlying evidence:

```json
{
  "statement_id": "STMT-S2-81A4F2",
  "section_index": 2,
  "section_title": "Requested Procedure",
  "sentence_text": "Proposed Treatment Plan: Molar Endodontic Therapy on Tooth #46 (Candidate CDT: D3330) [Urgency: URGENT].",
  "cited_evidence_ids": [
    "PROC-EVAL-001"
  ],
  "source_types": [
    "clinical_rationale"
  ],
  "verification_status": "confirmed_by_clinician",
  "uncertainty_preserved": true
}
```

### Traceability Rules:
1. **Model Observations (`EVID-RAD-*`):** Citations must link to the vision model finding UUID, annotated coordinate bounding box / polygon, and preserve uncertainty indicators.
2. **Dentist Review Decisions (`EVID-CFM-*`):** Citations must link to the reviewer name, license number, and timestamp.
3. **Clinical Tests (`EVID-EXM-*`):** Citations must link to chairside pulp vitality, percussion tenderness, and probing depths.
4. **Treatment Justifications (`PROC-*`):** Citations must link to clinician-entered rationale.
5. **No Evidence -> Flagged / Rejection:** If a substantive statement has no linked evidence ID, the Faithfulness Checker rejects the narrative or flags the claim as `unsupported_claim`.
