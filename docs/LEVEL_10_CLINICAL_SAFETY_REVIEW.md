# DENTRACE Level 10: Comprehensive Clinical Safety & AI Governance Audit

> **CLINICAL NOTICE:** *"Draft for dentist review. Not a diagnosis."*  
> **AUDITOR ROLE:** Principal Clinical AI Safety Reviewer & Medical Governance Lead  
> **DATE:** October 22, 2026

---

## 1. Regulatory Status & Clinical Boundary Definition

1. **Non-Medical Device Declaration**:
   - DENTRACE is an academic prototype and decision-support system.
   - It is **not** an FDA 510(k) cleared, CE-marked, or EU MDR (2017/745) certified Software as a Medical Device (SaMD).
   - Under no circumstances may DENTRACE outputs be utilized for autonomous clinical diagnosis, definitive surgical planning, or automated insurance pre-authorization approval.

2. **Immutable Legal Notice**:
   - The exact statutory notice:
     `"Draft for dentist review. Not a diagnosis."`
     is hardcoded into:
     - FastAPI REST API response payloads and HTTP headers
     - Streamlit clinical workstation headers and footers
     - Interactive canvas overlays
     - Generated ReportLab PDF claim packs (running header and attestation block)
     - Desktop supervisor launcher console banners

---

## 2. Clinical Safety Guardrails & Human-in-the-Loop Gates

```
       +-------------------------------------------------------------+
       |             OPG Radiograph Intake & Validation              |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |         Multi-Stage Neural Inference (Provisional)          |
       |  - YOLOv8n-Seg (DENTEX weights): Caries, Deep Caries,       |
       |    Periapical Lesions, Impacted Teeth                       |
       |  - Pretrained Anatomical FDI 32-Tooth Locator               |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |             Deterministic Clinical Rule Layer               |
       |  - Concept Separation: AI Observations vs Clinician Facts   |
       |  - FDI Ambiguity Gate: Unconfirmed Tooth -> BLOCKED         |
       |  - Bone Loss Gate: Missing Landmarks -> UNSUPPORTED         |
       |  - Endodontic Gate: Past Obturation != Autonomous Failure   |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |               MANDATORY CLINICIAN REVIEW GATE               |
       |  [!] Inspect and validate visual polygon masks on canvas    |
       |  [!] Verify FDI tooth numbers on interactive odontogram      |
       |  [!] Enter chairside clinical findings (vitality, probing)  |
       |  [!] Explicitly APPROVE, MODIFY, or REJECT each finding     |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |             Grounded Narrative & Pre-Auth Draft             |
       |  - Local Ollama qwen2.5:3b (Strict Pydantic JSON schema)    |
       |  - FaithfulnessChecker rejects unobserved teeth/conditions  |
       |  - Auto-reverts to deterministic template if unfaithful     |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |              ReportLab PDF Pre-Authorization Pack           |
       |  - Physical pen-and-ink signature block (Zero fake sigs)    |
       |  - Watermarked "PROVISIONAL REVIEW DRAFT" until signed      |
       |  - Explicit statement: "Does NOT guarantee claim approval"  |
       +-------------------------------------------------------------+
```

---

## 3. Specific Clinical Safety Violations & Enforced Mitigations

### 3.1 Unconfirmed Tooth Assignment Gate (`BLOCKED_BY_UNCONFIRMED_TOOTH`)
- **Safety Risk**: In crowded or partially edentulous arches, dental numbering algorithms can produce off-by-one errors (e.g., mislabeling tooth 14 as 15). Filing an insurance claim or performing restorative treatment on the wrong tooth constitutes severe medical malpractice.
- **Enforced Control**:
  - Tooth proposals with low confidence or topological ambiguity are flagged as `UNCONFIRMED`.
  - The pre-authorization engine strictly blocks pre-auth documentation generation (`BLOCKED_BY_UNCONFIRMED_TOOTH`) until a licensed practitioner manually inspects and confirms the tooth assignment on the interactive odontogram.

### 3.2 Alveolar Bone Loss Hallucination Prevention (`UNSUPPORTED_MISSING_LANDMARKS`)
- **Safety Risk**: Measuring horizontal or vertical bone loss requires three anatomical landmarks defined by the 2017 AAP/EFP World Workshop:
  1. Cementoenamel junction (CEJ)
  2. Alveolar bone crest line
  3. Root apex (for root length ratio)
  Attempting to calculate bone loss percentages without these landmarks results in fabricated clinical metrics.
- **Enforced Control**:
  - DENTEX and public OPG datasets lack CEJ and crest line segmentations.
  - DENTRACE systematically refuses to invent or extrapolate bone loss numbers, returning status `UNSUPPORTED_MISSING_LANDMARKS`.

### 3.3 Endodontic Assessment & Failure Semantics
- **Safety Risk**: An endodontically treated tooth displays a dense radiopaque gutta-percha root canal filling. A prior obturation is restorative evidence of past therapy, not an active acute disease. Automatically labeling every treated tooth as a "failed root canal" causes unnecessary retreatments or extractions.
- **Enforced Control**:
  - Class 7 from `8024` model is classified as past restorative therapy (`radiopaque`).
  - Only when a tooth exhibits **both** past obturation AND a concurrent periapical radiolucency does the system generate an advisory:
    `"Previously treated tooth with suspected periapical radiographic finding — requires clinician review."`
  - It explicitly instructs the dentist to perform vitality testing, percussion, and palpation before diagnosing failure.

### 3.4 Zero Fabricated Practitioner Signatures
- **Safety Risk**: Generating synthetic digital signatures or mock dentist credentials on claim packets gives an illusion of licensed clinician authorization.
- **Enforced Control**:
  - ReportLab PDF export leaves a clear, bordered physical signature and license number entry box for ink-on-paper clinician attestation.
  - Zero digital signature graphics or auto-signed stamps are permitted.

### 3.5 No Claims of Guaranteed Insurance Reimbursement
- **Safety Risk**: Presenting pre-authorization paperwork as "guaranteed approval" misleads both clinic staff and patients regarding financial liability.
- **Enforced Control**:
  - All documentation clearly states:
    `"Pre-authorization documentation generated for payer evaluation only. Does not guarantee insurance claim approval, coverage eligibility, or reimbursement amount."`
