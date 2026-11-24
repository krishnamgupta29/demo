# DENTRACE — System Architecture & Technical Specification

> **DOCUMENT ID:** DOC-ARCH-006  
> **STATUS:** LEVEL 6 IMPLEMENTED & VERIFIED  
> **DATE:** 2026-10-20  

---

## 1. High-Level System Architecture

DENTRACE is organized as a decoupled, local-first medical AI application designed to run entirely offline on standard clinical hardware without external network transmission.

```
                              LOCAL HOST WORKSTATION (NO EXTERNAL EGRESS)
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                                                                                        │
 │  [Dental Radiograph (OPG)]                                                             │
 │            │                                                                           │
 │            ▼                                                                           │
 │  ┌─────────────────────────────────────┐                                               │
 │  │ 1. OPG File Intake & Privacy Shield │ ──► Strips DICOM/EXIF metadata                │
 │  └─────────────────────────────────────┘                                               │
 │            │                                                                           │
 │            ▼                                                                           │
 │  ┌─────────────────────────────────────┐                                               │
 │  │ 2. Automated Image Quality Screener │ ──► Aspect ratio, blur, resolution check      │
 │  └─────────────────────────────────────┘                                               │
 │            │                                                                           │
 │            ▼                                                                           │
 │  ┌─────────────────────────────────────────────────────────────────┐                   │
 │  │ 3. Multi-Model Vision Pipeline & Dynamic Model Registry         │                   │
 │  │   ┌───────────────────────────────┐ ┌─────────────────────────┐ │                   │
 │  │   │ 3A. Tooth Numbering Engine    │ │ 3B. Multi-Model Engine  │ │                   │
 │  │   │     FDI Boxes (11–48)         │ │     - DENTEX 4-Class Seg│ │                   │
 │  │   │     Calibrated Arch Pitch     │ │     - Nsitnov Restor/End│ │                   │
 │  │   │     Slot > 8 Abstention       │ │     - Liodon Screener   │ │                   │
 │  │   │                               │ │     - Dynamic INT8 ONNX │ │                   │
 │  │   └───────────────────────────────┘ └─────────────────────────┘ │                   │
 │  └─────────────────────────────────────────────────────────────────┘                   │
 │            │                                   │                                       │
 │            ▼                                   ▼                                       │
 │  ┌─────────────────────────────────────────────────────────────────┐                   │
 │  │ 4. Geometric Matcher & Calibrated Topological Arch Solver       │                   │
 │  │    - Spatial overlap ratio matching (>15%)                      │                   │
 │  │    - Max 8 teeth per quadrant rule & supernumerary abstention   │                   │
 │  │    - Tooth-width anatomical pitch scaling (canines vs molars)   │                   │
 │  │    - True polygon instance masks vs detection bounding box      │                   │
 │  └─────────────────────────────────────────────────────────────────┘                   │
 │            │                                                                           │
 │            ▼                                                                           │
 │  ┌─────────────────────────────────────────────────────────────────┐                   │
 │  │ 5. DETERMINISTIC CLINICAL RULE LAYER (Authoritative Governance) │                   │
 │  │    - Assigns: Tooth #, Condition, Category, Demo CDT Code       │                   │
 │  │    - Decides: Clinical Urgency ('routine', 'soon', 'urgent')    │                   │
 │  │    - Flags: Suspected Endodontic Failure (RCT + Periapical)     │                   │
 │  │    - Blocks: Bone Loss (UNSUPPORTED_MISSING_LANDMARKS)          │                   │
 │  │    - Emits: "Needs periapical radiograph" mandatory hint        │                   │
 │  └─────────────────────────────────────────────────────────────────┘                   │
 │            │                                                                           │
 │            ▼                                                                           │
 │  ┌─────────────────────────────────────────────────────────────────┐                   │
 │  │ 6. Bidirectional Faithfulness Validator & Local Ollama Engine  │                   │
 │  │    - Local Ollama (qwen2.5:3b-instruct / phi3:mini)             │                   │
 │  │    - Pydantic JSON Schema Format Constraint                     │                   │
 │  │    - Bidirectional Faithfulness Check (Max 2 retries)           │                   │
 │  │    - Guaranteed Deterministic Fallback Template                 │                   │
 │  └─────────────────────────────────────────────────────────────────┘                   │
 │            │                                                                           │
 │            ▼                                                                           │
 │  ┌─────────────────────────────────────────────────────────────────┐                   │
 │  │ 7. Clinical Interface & Document Generation                     │                   │
 │  │    - Streamlit UI with custom HTML5 Canvas Mask Viewer          │                   │
 │  │    - Interactive FDI Odontogram & Findings Table                │                   │
 │  │    - Two-Page ReportLab PDF Claim Pack with Dentist Sign-Off    │                   │
 │  │    - Local SQLite Audit Ledger                                  │                   │
 │  └─────────────────────────────────────────────────────────────────┘                   │
 │                                                                                        │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Hardware Budget & Resource Allocation

| Resource | Available Host Capacity | DENTRACE Allocation / Limit | Strategy & Mitigation |
|---|---|---|---|
| **OS** | Windows 11 x64 | Windows 11 x64 Native | Standardized PowerShell scripts and cross-platform path handling (`pathlib.Path`). |
| **Python** | Python 3.11.9 (`py -3.11`) | Dedicated Python 3.11 virtual environment | Enforced via `.env` and scripts. Prevents Python 3.13 / 3.15 bytecode incompatibility. |
| **CPU** | Multi-core x86_64 host | 4 Intra-op Threads | Target CPU inference latency: ~312–874ms. Sub-50ms CPU claim disproven and audited. |
| **GPU** | NVIDIA RTX 2050 (4 GB VRAM) | Max 3.2 GB Allocated | Batch size $\le 8$, mixed-precision FP16. Local fine-tuning verified (peak VRAM: 0.828 GB). |
| **RAM** | ~16 GB Physical | Peak working set $\le 6\text{ GB}$ | Streaming image buffers, on-demand session loading, lightweight models. |
| **Storage (C:)** | ~150 GB Free | Primary Storage for Datasets & Models | Pip wheels, HuggingFace caches, Ollama model weights stored here. |
| **Storage (D:)** | **~4.58 GB Free** | Codebase & Project Config ONLY | **ZERO DATASETS ON D:.** Enforced by `.gitignore` and `.env.example`. |

---

## 3. Pipeline Step Specifications

### Step 1: OPG Intake & Privacy Shield
- Accepts PNG, JPG, or DICOM files.
- Strips all patient metadata (Patient Name, DOB, Institution, Machine Serial Number) before memory staging.
- Assigns an anonymous unique Case ID: `CASE-[UUID8]`.

### Step 2: Automated Image Quality Screening
- Evaluates:
  1. Resolution: Flags images $<900\times 450$ px.
  2. Aspect Ratio: Flags images with aspect ratio $<1.4:1$ (non-panoramic crop).
  3. Blur: Computes Laplacian variance. Scores $<50.0$ trigger a "Motion blur / quality caution" alert.

### Step 3: Multi-Model Vision Pipeline & Model Registry (Level 6 - COMPLETE)
- **Model Registry (`backend/services/model_adapter.py`):** Central auditable registry managing 8 model candidate configurations with cryptographic SHA-256 integrity verification, execution providers, and license tracking.
- **Candidate 1 (`abychkov-fdi-detection`):** FDI permanent tooth detector (11–48) using RT-DETR transformer architecture.
- **Candidate 2 & 8 (`liodon-panoramic-screener` & INT8):** Fast anomaly screening (caries, periapical lesions, impacted teeth) at 312 ms CPU latency; 2.87 MB INT8 footprint.
- **Candidate 4 & 5 (`dentex-yolov8n-seg` & INT8):** In-house fine-tuned 4-class instance segmenter on 3,529 authoritative DENTEX annotations. Outputs true polygon masks tracing whole abnormal tooth envelopes.
- **Candidate 6 & 7 (`nsitnov-8024-seg` & INT8):** Restorations and endodontics 8-class segmentation model. Distinguishes Class 7 `Root-Canal-Treatment` (radiopaque past restoration) from Class 5 `Periapical-lesion` (active radiolucency).
- **Candidate 3 (`boneloss-pan769-baseline`):** Formally blocked with `UNSUPPORTED_MISSING_LANDMARKS` citing the biological necessity of CEJ, crest line, and root apex landmarks. Zero fabricated bone loss.

### Step 4: Calibrated Geometric Matcher & Topological Arch Solver (Level 6 - COMPLETE)
- **Calibrated Anatomical-Prior Solver (`CalibratedFDISolver`):**
  - Incorporates tooth-specific anatomical crown width ratios (`MAXILLA_WIDTH_FACTORS`, `MANDIBLE_WIDTH_FACTORS`).
  - Corrects 94.6% of historical baseline errors caused by intra-quadrant enumeration shifts.
  - Implements an abstention mechanism: teeth exceeding the 8-tooth human quadrant limit or exhibiting unresolvable pitch anomalies are designated `fdi_number = None` and flagged `uncertain_tooth = True`.
  - Reaches **76.07% exact accuracy** and **76.55% precision** across 4,224 audited teeth.
- **Modality Preservation:** Distinguishes genuine instance segmentation polygons (`AnnotationModality.INSTANCE_SEGMENTATION`) from rectangular detection proposals (`AnnotationModality.DETECTION_BOUNDING_BOX`). Bounding boxes are never falsified as pixel masks.
- Associates findings with host tooth using spatial overlap:
  $$\text{Overlap Ratio} = \frac{\text{Area}(\text{Pathology} \cap \text{Tooth})}{\text{Area}(\text{Pathology})} \ge 0.15$$

### Step 5: Deterministic Clinical Evidence Engine & Concept Separation (Level 4 - COMPLETE)
- Authoritative governance layer executing strictly BEFORE natural language drafting.
- Enforces three-way conceptual separation:
  * Concept A: AI Radiographic Observations (`RadiographicObservation`, unverified until clinician review).
  * Concept B: Clinician Verified Facts (`DentistFindingConfirmation`, `ClinicalExaminationRecord`, `PatientSymptomRecord`).
  * Concept C: Insurance Pre-Auth Requirements (`RequestedProcedureRecord`, `PayerPolicyTemplate`).
- **Missing Evidence Detective (`MissingEvidenceDetective`):**
  * Audits clinical documentation requirements across specialty procedures (Endodontics, Restorative, Oral Surgery, Periodontics).
  * Flags missing pulp vitality tests, percussion tenderness, structural cavitation, or periodontal probing depths.
  * Enforces the Mandatory Modality Rule: OPG screening requires supplemental Intraoral Periapical (IOPA) radiograph for root canal claims.
- **Preflight Readiness Engine (`EvidenceReadinessReport`):**
  * Detects clinical contradictions (e.g., vital pulp endodontics, procedure on rejected finding, CDT anatomical mismatch).
  * Enforces tooth confirmation: ambiguous or shifted tooth numbers trigger `BLOCKED_BY_UNCONFIRMED_TOOTH`.
  * Computes transparent checklist completeness percentage (explicitly NOT approval likelihood).

### Step 6: Schema-Constrained Local Ollama Engine & Faithfulness Validator (Level 4 - COMPLETE)
- Local Ollama daemon running strictly on localhost loopback (`127.0.0.1:11434`, zero cloud egress).
- Verified target model: `qwen2.5:3b` (3.1B parameters, Q4_K_M GGUF, 1.93 GB on C:).
- Strict prompt injection defense using XML-compartmentalized structured clinical facts.
- Generates 10 standard clinical pre-authorization documentation sections.
- **Deterministic Faithfulness Checker (`FaithfulnessChecker`):**
  * Audits narrative statements sentence-by-sentence with bidirectional claim-to-evidence traceability.
  * Rejects ungrounded tooth numbers, hallucinated pathologies, and unpreserved certainty claims.
  * Automatic deterministic fallback: Reverts to `DeterministicNarrativeGenerator` upon any faithfulness failure, malformed JSON, or Ollama offline state.

### Step 7: Clinical Workstation UI & ReportLab Claim Pack PDF (Level 5 - COMPLETE)
- Streamlit 1.39+ clinical decision-support workstation running on `127.0.0.1:8501`.
- Curie-Nordic Dark Obsidian design tokens (`#070A0D` canvas, `#0D1217` shell, `#131B22` panels).
- Reusable HTML5 Canvas viewer (`frontend/components/canvas_viewer.py`) with 60 FPS pan/zoom, 1:1 grayscale pixel preservation, true polygon instance masks vs bounding boxes toggles, tooth overlays, and hover tooltips.
- Interactive permanent adult 32-tooth odontogram (`frontend/components/odontogram.py`) partitioned into 4 anatomical quadrants (FDI 11–48).
- Complete 7-screen clinical workflow: Welcome Overview, Study Intake / Upload, Diagnostic Workstation, FDI Explorer, Findings & Evidence, Insurance Pre-Auth Studio, and System Diagnostics / Model Registry.
- Two-page clinical PDF claim pack generator with running headers/footers, draft watermarks, and physical dentist signature/license attestation space.
- Immutable, tamper-evident SQLite audit ledger tracking all clinical adjudications.

### Step 8: System Hardening, Security, Privacy & Reliability (Level 8 - COMPLETE)
- Security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options) and restricted CORS (`127.0.0.1:8501`).
- Path traversal defense, file magic-byte validation, and SHA-256 weight integrity enforcement.
- DICOM de-identification (11 core tags scrubbed, zero file log handlers, zero stack trace leakage).
- SQLite concurrency protection (Write-Ahead Logging `PRAGMA journal_mode=WAL`, transactional rollbacks, foreign keys, cascade deletes).
- Regulatory disclaimers across all endpoints, UI screens, and PDF exports.
- Multi-model selection endpoint (`/api/models/select`) with GPU VRAM monitoring.

### Step 9: Windows Desktop Packaging, Offline Installation & Release Validation (Level 9 - COMPLETE)
- **Native Process Supervisor & Launcher (`scripts/launcher/launcher.py`, `launch_dentrace.bat`, `launch_dentrace.ps1`)**:
  * Single-instance mutual exclusion file lock (`.dentrace.lock`) preventing duplicate server bindings and DB corruption.
  * 5 preflight health gates: port availability (8000/8501), SQLite WAL migration check, neural weight SHA-256 verification, NVIDIA RTX 2050 CUDA detection, and Ollama probe.
  * Zero-orphan process tree termination (`taskkill /F /T /PID`) on console exit or interrupt.
- **Local Access Security**: Ephemeral 256-bit session token (`X-DENTRACE-TOKEN`) generated by launcher and enforced across all mutative backend endpoints.
- **Deep DICOM Privacy Hardening**: 18-tag standard PHI scrub, recursive vendor private tag purging, and non-destructive burned-in text detection.
- **User-Isolated Storage Architecture**: All runtime databases, DICOM stores, and exported clinical PDFs reside in `%LOCALAPPDATA%\DENTRACE\data` (complying with standard Windows user UAC privileges).
- **Release Automation (`scripts/build_release.py`)**:
  * Automated clean staging into `dist/DENTRACE-v0.1.0-win64` (excluding tests, caches, datasets, and unanonymized files).
  * Cryptographic manifest generation (`dist/SHA256SUMS.txt`).
  * Compressed portable release archive (`dist/DENTRACE-v0.1.0-win64.zip`, ~446.59 MB).
  * Inno Setup installer script generation (`scripts/installer/dentrace_setup.iss`).

