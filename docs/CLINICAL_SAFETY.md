# DENTRACE — Clinical Safety, Ethics & Privacy Governance

> **DOCUMENT ID:** DOC-SAFE-005  
> **STATUS:** BASELINED (LEVEL 0)  
> **DATE:** 2026-10-18  

---

## 1. Ethical & Regulatory Boundary

### A. Non-Diagnostic Academic Prototype
DENTRACE is developed strictly as an academic decision-support prototype. It is **not a medical device** and has not been certified or cleared by the US FDA (510(k)), European Union Medical Device Regulation (EU MDR 2017/745), or the Central Drugs Standard Control Organisation (CDSCO). 

### B. Mandatory Clinical Banner
Every screen, report, data export, and API payload that displays findings or generated narratives must carry the unalterable notice:
> **"Draft for dentist review. Not a diagnosis."**

The software must never claim autonomous diagnosis, independent treatment planning, or automated insurance approval.

---

## 2. Modality Diagnostic Limitations (OPG Radiography)

Dental panoramic radiographs (OPGs) are screening tools with inherent physical and geometric constraints:

1. **Magnification & Distortion:**
   - Panoramic machines use tomography with curved focal troughs. Structures outside the focal trough appear distorted, magnified, or blurred.
   - *Clinical Rule:* Absolute millimetric measurements (e.g., bone loss in millimeters) cannot be claimed without physical calibration markers. Bone loss must be documented as qualitative or crown-to-root ratios.
2. **Proximal Contact Overlap:**
   - Teeth with severe crowding or rotated bicuspids/molars overlap on 2D projections.
   - *Clinical Rule:* Caries detection on overlapping surfaces represents a radiolucent suspicion, not definitive cavitation. Occlusal and early enamel lesions require clinical inspection and bitewing confirmation.
3. **Ghost Images & Cervical Burnout:**
   - Radiopaque ghost shadows from the contralateral mandible, palate, and hyoid bone can mimic pathology or obscure root apices.
   - Cervical burnout (optical radiolucency at tooth necks) must not be misclassified as root caries.
4. **Apical Pathology & Endodontic Failure:**
   - Superimposition of the mandibular canal or mental foramen over mandibular bicuspid apices can mimic periapical lesions.
   - *Clinical Rule:* Whenever a periapical lesion or suspected endodontic failure is detected, the system mandates: *"Requires intraoral periapical radiograph for apical resolution."*

---

## 3. Threat Assessment & Privacy Boundaries

| Threat / Risk Vector | Severity | Vulnerability Description | DENTRACE Defensive Control |
|---|---|---|---|
| **Patient Data Cloud Leakage** | High | Ingestion of radiographs transmitting PHI/PII to external cloud APIs (e.g., OpenAI, Google, AWS). | **Total Offline Boundary:** All inference executes on localhost (`127.0.0.1`). Streamlit usage tracking disabled (`browser.gatherUsageStats = false`). The only network interaction is to local Ollama on loopback. |
| **DICOM / EXIF Metadata Leakage** | Medium | Embedded patient names, hospital IDs, or birthdates stored in image headers. | **Header Sanitization:** File intake strips metadata during memory decoding; images are re-encoded into anonymous raster buffers before processing. |
| **LLM Diagnostic Hallucination** | Critical | Language models fabricating tooth numbers, unverified cavities, or altered urgency levels. | **Deterministic Rule Governance:** The LLM is strictly forbidden from diagnosing. It only rewrites verified facts passed from the deterministic rule layer under a Pydantic JSON schema format constraint with a bidirectional faithfulness checker. |
| **CDT Copyright Infringement** | Medium | Distributing copyrighted Current Dental Terminology code books. | **Demo Subset Only:** Uses a small illustrative subset in `config/cdt_demo.json` with an explicit ADA copyright disclaimer instructing clinicians to cross-reference current official code sets. |
| **Silent Model Failure** | High | Unconfident or out-of-distribution OPGs producing misleading detections. | **Automated Quality Screener:** Rejects corrupted files, warns on extreme blur (Laplacian $<50$) or low resolution ($<900\times 450$), and exposes an interactive confidence slider for clinician thresholding. |

---

## 4. Human-in-the-Loop Workflow

```
 AI Vision Model Prediction
            │
            ▼
 Deterministic Clinical Rules ──► Evaluates Urgency & Endo Failure
            │
            ▼
 Local LLM Narrative Draft
            │
            ▼
 ┌─────────────────────────────────────────────────────────┐
 │ CLINICIAN REVIEW GATE (Mandatory Human Intervention)    │
 │ - Review color-coded masks on interactive canvas        │
 │ - Inspect FDI tooth numbering on odontogram             │
 │ - Edit/correct narrative medical necessity justification│
 │ - Approve or reject individual findings                 │
 └─────────────────────────────────────────────────────────┘
            │
            ▼
 Dentist Physical Signature Line on Finalized Claim Pack PDF
```
No claim pack PDF can be submitted to an insurance payer without a licensed dental practitioner's clinical attestation and signature.
