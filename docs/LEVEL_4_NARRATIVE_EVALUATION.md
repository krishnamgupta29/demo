# DENTRACE Level 4: Narrative Synthesis Evaluation & FDI Reconciliation

**Document ID:** `DOC-EVAL-L4-004`  
**Date:** 2026-10-20  
**Status:** COMPLETE & AUTHORITATIVE  
**Notice:** *"Draft for dentist review. Not a diagnosis. Software evaluation, not clinical trial."*

---

## 1. Ten Mandatory Narrative Sections

Every generated pre-authorization draft (`InsurancePreAuthDraft`) complies with the 10 standard clinical pre-authorization sections required by dental payers:

```
Section 1:  Case Identification (Study UUID, Radiograph ID, Timestamp)
Section 2:  Requested Dental Procedure (Treatment, Candidate CDT, Urgency)
Section 3:  Tooth Identifier (FDI Designation, Clinician Verification State)
Section 4:  Clinician-Confirmed Findings (Attested Pathologies, Notes, Reviewer Identity)
Section 5:  Radiographic Observations (AI-Suspected Findings with Uncertainty Preserved)
Section 6:  Supporting Evidence References (Image Crops, Vitality, Percussion, Probing)
Section 7:  Clinical Rationale Supplied by the Treating Dentist
Section 8:  Pre-Authorization Documentation Checklist (Pending / Missing Items)
Section 9:  CDT Procedure Code References (Illustrative Demonstrative Metadata)
Section 10: Mandatory Reviewer Attestation (Regulatory Boundary & Signature Notice)
```

---

## 2. Representative Synthetic Clinical Scenarios & Narrative Outputs

### Scenario 1: Mandibular Molar Endodontics (Tooth #46)
- **Input Evidence:** Deep caries near pulp, confirmed by Dr. Eleanor Vance (DEN-90142), pulp vitality: non-vital, percussion: sensitive, procedure: Molar Endodontic Therapy (CDT D3330).
- **Generated Narrative Sample:**
  > **1. Case Identification:** Case Study ID: STUDY-EVAL-001. Associated Radiograph ID: eval_opg_46.png. Record generated on 2026-10-20 UTC under academic decision-support protocol.  
  > **2. Requested Procedure:** Proposed Treatment Plan: Molar Endodontic Therapy on Tooth #46 (Candidate CDT: D3330) [Urgency: URGENT].  
  > **3. Tooth Identifier:** Clinician-verified FDI tooth identifier(s): 46.  
  > **4. Clinician Confirmed Findings:** Clinician Findings: Reviewer Dr. Eleanor Vance, DDS (Lic# DEN-90142) CONFIRMED deep_caries on Tooth #46 with notes: 'Deep distal caries approximating pulp canal space with chronic pulpitis.'.  
  > **5. Radiographic Observations:** Radiographic Observations: Screening analysis detected: Model liodon-panoramic-screener (1.0.0) suspected deep_caries near Tooth #46 [raw confidence: 91.0%, modality: detection_bounding_box]. These represent provisional observations, not definitive diagnoses.  
  > **6. Supporting Evidence References:** Supporting Evidence Catalog: Image Assets: Full OPG raster. Clinical Tests: Exam [EVID-EXM-001]: Vitality=non_vital, Percussion=True, Cavitation=True.  
  > **7. Clinical Rationale:** Clinician Clinical Rationale: Procedure 'Molar Endodontic Therapy': Necrotic pulp with symptomatic apical periodontitis substantiated by non-vital response and percussion tenderness.  
  > **8. Missing Documentation Checklist:** Pre-Authorization Documentation Checklist (Pending Items):  
  > - Has an intraoral periapical radiograph been taken and attached for tooth 46? (Mandatory Modality Rule: Panoramic radiographs have focal trough distortion. Endodontic therapy pre-authorization requires an intraoral periapical (IOPA) radiograph for root apex visualization.)  
  > **9. Procedure Code References:** CDT Procedure Code References (Illustrative Demo Catalog 2026): D3330 (Dentist-Attested): Molar Endodontic Therapy. Notice: Code inclusion does not guarantee insurance coverage or payment.  
  > **10. Mandatory Reviewer Attestation:** MANDATORY CLINICAL REVIEW ATTESTATION: Draft for dentist review. Not a diagnosis. This pre-authorization narrative is an academic clinical decision-support draft. It does not constitute autonomous medical advice, treatment determination, or guaranteed payer authorization. Submission requires pen-and-ink or authenticated digital attestation by the licensed treating dentist.

---

## 3. Faithfulness Evaluation & Hallucination Interception

The `FaithfulnessChecker` (`backend/clinical/faithfulness.py`) was evaluated on standard clinical cases as well as deliberate adversarial injection scenarios:

| Test Case | Scenario Description | Expected Outcome | Actual Result | Verification |
|---|---|---|:---:|:---:|
| **Standard Baseline** | Valid Scenario 1 (Tooth #46, deep caries) | 100% faithful, zero ungrounded claims | `is_faithful = True` | **PASS** |
| **Adversarial Tooth Injection** | Injected mention of ungrounded Tooth #35 | Caught by entity extractor, flagged as hallucinated | Intercepted (`teeth: [35]`) | **PASS** |
| **Adversarial Pathology Injection** | Injected mention of `alveolar_bone_loss` | Caught by taxonomy matcher, flagged as unsupported | Intercepted (`claim: ungrounded`) | **PASS** |
| **Certainty Violation Injection** | Removed uncertainty words ("definitively confirms caries") | Flagged as ungrounded clinical assertion | Intercepted (`uncertainty violation`) | **PASS** |
| **Adversarial Defense Catch Rate** | Aggregate of all adversarial tests | **100.0% Interception** | **100.0% Interception** | **PASS** |

---

## 4. Subgroup FDI Tooth Numbering Accuracy Reconciliation

A core mandate of Level 4 safety is to independently reconcile subgroup FDI accuracy figures against total accuracy:

### 4.1. Reconciliation Audit Table

$$N = 4,224\text{ teeth across 150 panoramic radiographs}$$

| Level / Solver Variant | Subgroup Decomposition | Accuracy | Correct / Total Teeth | Mathematical Reconciled Sum |
|---|---|:---:|:---:|---|
| **Baseline Heuristic (Jaw)** | Maxilla (Upper Jaw)<br/>Mandible (Lower Jaw) | 78.32%<br/>70.79% | 1,651 / 2,108<br/>1,498 / 2,116 | $1,651 + 1,498 = 3,149 / 4,224 = \mathbf{74.55\%}$ |
| **Baseline Heuristic (Quadrant)** | Q1 (Maxillary Right)<br/>Q2 (Maxillary Left)<br/>Q3 (Mandibular Left)<br/>Q4 (Mandibular Right) | 78.81%<br/>77.83%<br/>71.67%<br/>69.91% | 833 / 1,057<br/>818 / 1,051<br/>759 / 1,059<br/>739 / 1,057 | $833 + 818 + 759 + 739 = 3,149 / 4,224 = \mathbf{74.55\%}$ |
| **Tuned Topological Solver** | All Quadrants Combined | **78.06%** | **3,297 / 4,224** | $+148\text{ teeth corrected}$ via duplicate NMS and occlusal split |
| **Tuned Solver (Non-Abstained)** | Abstaining on ambiguous gaps | **80.35%** | **3,297 / 4,103** | $121\text{ teeth safely abstained}$ (2.85% abstention rate) |

### 4.2. Clinical Significance
1. **Mathematical Consistency:** The subgroup sums ($1,651 + 1,498 = 3,149$ and $833 + 818 + 759 + 739 = 3,149$) confirm that baseline heuristic accuracy is exactly **74.55%**.
2. **Topological Solver Gain:** The tuned solver achieves **78.06%** overall exact accuracy, and **80.35%** when abstaining on ambiguous tooth proposals.
3. **Clinical Safety Safeguard:** Because approximately 22% of automated tooth assignments in panoramic radiographs suffer from serial gap shifts or missing-tooth domino effects, **unconfirmed AI tooth proposals must never enter an insurance claim as confirmed facts**. The preflight engine strictly blocks claim packs until explicit human confirmation is recorded.
